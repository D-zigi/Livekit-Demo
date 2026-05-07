"""
Observer agent that monitors sales conversations for policy violations.

Implements the observer pattern described at:
https://livekit.com/blog/observer-pattern-voice-agent-guardrails

A background LLM evaluates transcripts asynchronously after each user turn.
When a violation is detected, a [POLICY: ...] system message is injected into
the active agent's chat context via update_instructions — without interrupting the call.
"""

import asyncio
import json
import logging
from typing import ClassVar

from livekit import rtc
from livekit.agents import AgentSession, ChatContext, ChatMessage, JobContext, llm
from livekit.agents import stt
from livekit.agents.stt import SpeechEventType
from livekit.agents.voice import ConversationItemAddedEvent

logger = logging.getLogger(__name__)


class PolicyObserver:
    """
    Monitors sales conversations for policy violations.

    Runs LLM evaluation after every user turn. If an eval is already running
    when a new turn arrives, a follow-up eval is scheduled to run immediately
    after, ensuring no content is skipped.

    When a violation is detected, injects a [POLICY: ...] system message into
    the active agent's chat_ctx via update_instructions. Each violation type is
    injected at most once per call to avoid noise.
    """

    VIOLATION_KEYS: ClassVar[list[str]] = [
        "competitor_mention",
        "pricing_boundary",
        "legal_compliance",
        "customer_escalation",
        "data_privacy",
    ]

    GUARDRAIL_HINTS: ClassVar[dict[str, str]] = {
        "competitor_mention": (
            "[POLICY: COMPETITOR MENTION] The prospect has mentioned a competitor. "
            "Acknowledge their familiarity with alternatives, then pivot to our unique value "
            "proposition. Do not speak negatively about competitors. Focus on differentiation."
        ),
        "pricing_boundary": (
            "[POLICY: PRICING BOUNDARY] The conversation has entered pricing territory that "
            "may exceed your authorization. Do not commit to discounts or custom pricing. "
            "Offer to connect them with the sales team for a tailored quote."
        ),
        "legal_compliance": (
            "[POLICY: LEGAL COMPLIANCE] The caller has raised a topic that may have legal "
            "or contractual implications. Do not make binding statements. "
            "Acknowledge the concern and offer to have the appropriate team follow up."
        ),
        "customer_escalation": (
            "[POLICY: ESCALATION] The customer appears frustrated or is requesting to speak "
            "with a manager. Acknowledge their frustration with empathy, stay calm, and offer "
            "to escalate to a senior representative if needed."
        ),
        "data_privacy": (
            "[POLICY: DATA PRIVACY] The caller has raised concerns about data handling, GDPR, "
            "or personal information. Reassure them of our compliance practices and offer to "
            "send our privacy policy. Do not make specific data-handling commitments."
        ),
    }

    def __init__(
        self,
        ctx: JobContext,
        session: AgentSession,
        stt: stt.STT,
        llm: llm.LLM
    ) -> None:
        self.ctx = ctx
        self.session = session
        self.stt = stt
        self.llm = llm
        self.conversation_history: list[dict] = []
        self.injected_violations: set[str] = set()
        self._evaluating = False
        self._pending_eval = False
        self._bg_tasks: set[asyncio.Task] = set()

        self._setup_listeners()
        logger.info("[OBSERVER] Policy observer attached to session")

    def _setup_listeners(self) -> None:
        @self.ctx.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.RemoteTrack):
            print(f"Subscribed to track: {track.name}")
            asyncio.create_task(process_track(track))

        async def process_track(track: rtc.RemoteTrack):
            stt_stream = self.stt.stream()
            audio_stream = rtc.AudioStream(track)

            async with asyncio.TaskGroup() as tg:
                # Create task for processing STT stream
                stt_task = tg.create_task(process_stt_stream(stt_stream))

                # Process audio stream
                async for audio_event in audio_stream:
                    stt_stream.push_frame(audio_event.frame)

                # Indicates the end of the audio stream
                stt_stream.end_input()

                # Wait for STT processing to complete
                await stt_task

        async def process_stt_stream(stream: stt.SpeechStream):
            try:
                async for event in stream:
                    if event.type == SpeechEventType.FINAL_TRANSCRIPT:
                        text = event.alternatives[0].text  # Final transcript is ready
                        logger.debug(f"Final transcript: {text}")
                        # Process the final transcript for policy evaluation
                        if not text.strip():
                            return  # Ignore empty transcripts
                        self.conversation_history.append({"role": "user", "text": text})
                        logger.debug(f"[OBSERVER] Buffered: {text[:80]}{'...' if len(text) > 80 else ''}")

                        task = asyncio.create_task(self._evaluate())
                        self._bg_tasks.add(task)
                        task.add_done_callback(self._bg_tasks.discard)
                    elif event.type == SpeechEventType.INTERIM_TRANSCRIPT:
                        pass
                    elif event.type == SpeechEventType.START_OF_SPEECH:
                        logger.debug("Start of speech")
                    elif event.type == SpeechEventType.END_OF_SPEECH:
                        logger.debug("End of speech")
            finally:
                await stream.aclose()

    async def _evaluate(self) -> None:
        """Run LLM-based policy evaluation on recent conversation history.

        Only one eval runs at a time. If a new user turn arrives while an eval
        is in flight, _pending_eval is set to True. When the current eval
        finishes, it schedules one follow-up run, so no content is ever
        skipped and concurrent LLM calls never pile up.
        """
        if self._evaluating:
            self._pending_eval = True
            return
        self._evaluating = True
        self._pending_eval = False
        try:
            recent = self.conversation_history[-10:]
            transcript = "\n".join(f"prospect: {m['text']}" for m in recent)

            prompt = f"""You are a compliance monitor for a sales call.
Analyze the prospect's statements below and return ONLY a JSON object, no prose.

Transcript:
{transcript}

Return this exact JSON structure:
{{
  "competitor_mention": false,
  "pricing_boundary": false,
  "legal_compliance": false,
  "customer_escalation": false,
  "data_privacy": false,
  "details": ""
}}
"""

            chat_ctx = ChatContext()
            chat_ctx.add_message(role="user", content=prompt)

            response_text = ""
            async with self.llm.chat(chat_ctx=chat_ctx) as stream:
                async for chunk in stream:
                    if chunk.delta and chunk.delta.content:
                        response_text += chunk.delta.content

            result = self._parse_response(response_text)
            if result:
                await self._process_violations(result)

        except Exception:
            logger.exception("[OBSERVER] Evaluation error")
        finally:
            self._evaluating = False
            if self._pending_eval:
                logger.info("[OBSERVER] Pending eval, re-running for accumulated turns")
                task = asyncio.create_task(self._evaluate())
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)

    def _parse_response(self, text: str) -> dict | None:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.warning(f"[OBSERVER] Could not parse response: {text[:100]}")
        return None

    async def _process_violations(self, result: dict) -> None:
        for key in self.VIOLATION_KEYS:
            if result.get(key) and key not in self.injected_violations:
                details = result.get("details", "")
                logger.warning(f"[OBSERVER] Violation: {key} — {details}")
                await self._inject_guardrail(key, details)
                self.injected_violations.add(key)

    async def _inject_guardrail(self, violation: str, details: str) -> None:
        """Inject a policy hint into the active agent's context.

        Copies the current chat context, appends a system message with the
        guardrail instruction, then updates the agent's context. The agent
        sees this on its next reply cycle without any interruption.
        """
        current_agent = self.session.current_agent
        if not current_agent:
            logger.warning("[OBSERVER] No active agent to inject into")
            return

        hint = self.GUARDRAIL_HINTS.get(violation, "")
        if details:
            hint = f"{hint}\n\nObserver analysis: {details}"

        await current_agent.update_instructions(hint)
        logger.info(f"[OBSERVER] Injected guardrail: {violation}")


def start_observer(
    *,
    ctx: JobContext,
    session: AgentSession,
    stt: stt.STT,
    llm: llm.LLM
) -> PolicyObserver:
    """Attach a PolicyObserver to the session. Returns immediately, non-blocking."""
    return PolicyObserver(ctx=ctx, session=session, stt=stt, llm=llm)
