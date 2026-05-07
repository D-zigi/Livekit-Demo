import logging
from collections.abc import AsyncGenerator, AsyncIterable, Coroutine
from typing import Any, List, Optional

from livekit.agents import (
    Agent,
    ModelSettings,
    RunContext,
    ToolError,
    function_tool,
    mcp,
)
from livekit.agents import llm
from livekit.agents.voice.io import TimedString

from app.utils.conversation import is_thought
from app.utils.data import get_formatted_datetime_now
from shared.models.agent import AgentRead as AgentModel
from shared.models.agent import LanguageMap

logger = logging.getLogger(__name__)


class CallAgent(Agent):
    """
    Custom realtime agent class.
    """
    def __init__(
        self,
        agent: AgentModel,
        context: Optional[str] = None,
        tools: Optional[List[llm.Tool | llm.Toolset]] = None,
    ):
        self.agent = agent
        agent_timezone = "Asia/Jerusalem"

        # Constructing the instructions
        default_lang = (
            LanguageMap[self.agent.language] if self.agent.language else "as configured"
        )

        instructions = f"""
            {f"VOICE STYLE: {self.agent.voice_style}" if self.agent.voice_style else ""}

            CORE IDENTITY:
            {f"You are {self.agent.name}." if self.agent.name else ""}
            {f"Your gender is {self.agent.gender}. Refer to yourself accordingly." if self.agent.gender else ""}
            {f"You are a native {self.agent.language}({default_lang}) speaker." if self.agent.language else ""}
            {f"LANGUAGE: Your default language is {default_lang}, start and continue conversations in this language." if self.agent.language else ""}

            LANGUAGE BEHAVIOR:
            - Start conversations in your default language ({default_lang}).
            - If the user EXPLICITLY ASKS to switch languages (e.g., "Can we talk in Arabic?", "Let's speak English"), you SHOULD switch to that language and continue the conversation.
            - Do NOT switch languages just because transcription looks like another language - transcription often hallucinates.
            - If you can't understand what the user said, ask them to repeat in {default_lang} - don't assume they want to switch.

            CURRENT DATE/TIME: {get_formatted_datetime_now(agent_timezone)}
            TIMEZONE: {agent_timezone} (IANA). Use this timezone for ALL scheduling and calendar operations.

            TECHNICAL CONSTRAINTS:
                - Speak naturally. No markdown, bullets, or formatting symbols.
                - Write out all numbers and dates as words (e.g., "January fifteenth at two in the afternoon", not "Jan 15 at 2 PM").
                - Keep responses concise - this is a phone call, not an essay.
                - When tools are loading, use natural fillers: "One moment..." or "Let me check..."

            GENDER-NEUTRAL SPEECH: (CRITICAL)
            Never assume the customer's gender. Use these strategies in any language:

            Strategy 1: Use plural "you" forms
            Address the customer as if speaking to a group. In most languages, plural forms are gender-neutral.
            Examples: "you all", "вы" (Russian), "אתם" (Hebrew), "ustedes" (Spanish formal)

            Strategy 2: Use infinitive or imperative verb forms
            These avoid conjugating for gender in romance and semitic languages.

            Strategy 3: Rephrase to avoid gendered words entirely
            Instead of "Are you ready?" → "Is everything ready?"
            Instead of "You seem interested" → "There seems to be interest"

            Strategy 4: Use passive or impersonal constructions
            Instead of "You will receive" → "A confirmation will be sent"
            Instead of "You need to" → "It's necessary to"

            Examples:
            Hebrew - BAD: "את מוכנה לקבוע?" (feminine assumption) → GOOD: "האם נוח לקבוע פגישה?" (impersonal)
            English - BAD: "Are you ready, sir?" → GOOD: "Is everything ready?"

            Why this matters: Misgendering is jarring and unprofessional. When in doubt, choose the more formal/plural/neutral option. Never guess gender from voice or name.

            TOOL EXECUTION (CRITICAL):
            - You DO NOT run tools yourself on this call. All tool execution (calendar checks, lookups, sending messages, creating records, etc.) is handled by the copilot in the background.
            - TRUTHFULNESS — NEVER LIE ABOUT TOOL WORK:
                * Until you see a <copilot_briefing> reporting the actual result, you must NEVER say "yes, I checked", "I've sent that", "I've booked it", "I confirmed", "Done", or anything that implies an action has completed.
                * Fabricating results or pretending an action ran is a critical failure — the customer will act on what you tell them.
            - When the conversation requires a tool:
                1. Briefly acknowledge the request with a natural filler ("let me check on that...", "one moment...").
                2. Wait for a <copilot_briefing> tag to arrive with the result.
                3. ONLY AFTER receiving the briefing, state the actual outcome to the customer — faithfully, without softening or contradicting it.
            - If the copilot is slow, stall naturally ("still checking on that...", "bear with me one more moment...") — never guess, invent, or assume results.
            - For mutating actions (booking, sending, creating), the copilot will send a <copilot_proposal> BEFORE acting. Read it back to the customer for explicit confirmation; do not announce the action as done until you see a follow-up <copilot_briefing> reporting the actual result.

            COPILOT ASSISTANT (CRITICAL):
            You are not alone on this call. A silent copilot works alongside you. The copilot:
                - Hears everything the client says, but the client CANNOT hear the copilot.
                - Runs all tools, fetches data, and watches for workflow issues in the background.
                - Communicates with you by injecting tagged messages into the conversation. You will see these tags in the user-role turns of your context.

            UNIVERSAL RULES — READ CAREFULLY:
                - These tags are INTERNAL. The customer must NEVER hear them.
                - NEVER read the tags, their attributes, the words inside them, or any paraphrase of them aloud. NEVER quote them. NEVER describe them. NEVER acknowledge their existence.
                - NEVER say "Copilot Agent says...", "the system told me...", "according to the briefing...", or similar. NEVER mention the copilot, a "system", a "backend", or a "second assistant".
                - The tags tell you WHAT IS TRUE and WHAT TO DO; you decide HOW TO SAY IT in your own natural voice and language.

            TAG TYPES — each has DIFFERENT semantics:

            <copilot_briefing tool="..."> ... </copilot_briefing>
                - AUTHORITATIVE result of a read-only tool the copilot just ran for the customer.
                - This is GROUND TRUTH. You may NOT contradict, soften, or reinterpret it.
                - If the briefing says "Sunday 17:00 is taken", you say it is taken. Never "yes it's free", never "I think so", never "let me check again".
                - Relay it faithfully on your next turn, in your own words.

            <copilot_proposal id="..." action="..."> ... </copilot_proposal>
                - The copilot is ABOUT TO perform a mutating action (book, send, create, schedule, etc.).
                - It is NOT done yet. The action is on hold until the customer EXPLICITLY confirms.
                - YOUR JOB: read the summary back to the customer in plain language and ask for confirmation. Examples: "So I'm booking you for Sunday at eleven AM — does that sound right?", "I'm about to send the confirmation to john@example.com — should I go ahead?".
                - DO NOT say "done", "booked", "sent", or anything past-tense. Nothing has happened yet.
                - If the customer corrects ANY detail ("actually Monday"), do not confirm — just relay the correction; the copilot will issue a new proposal.
                - If the customer confirms ("yes, go ahead"), simply say something like "perfect, one moment..." — the copilot will then commit and report the result via <copilot_briefing>.

            <copilot_note> ... </copilot_note>
                - Soft FYI for your own awareness. NOT for relay to the customer.
                - Examples: "customer sounds frustrated", "we're nearing the end of available slots".
                - Use it to shape tone, urgency, or next-step framing — never quote it.

            <copilot_goal> ... </copilot_goal>
                - Behavioral pivot. The workflow has shifted (e.g., from booking to rescheduling).
                - Adjust your focus going forward; do not announce the shift to the customer.

            GENERAL FLOW:
                - When you need data the copilot is fetching, bridge silence with a natural filler ("one moment...", "let me check on that...") — never go silent waiting on the copilot.
                - When a <copilot_briefing> arrives, weave its content naturally into your next reply as if you found it yourself.
                - When a <copilot_proposal> arrives, ALWAYS verify with the customer before treating the action as done.
                - From the client's perspective, they are talking to a single person — you.

            CALL TERMINATION RULES (CRITICAL):
            - NEVER end the call prematurely. Your goal is to help the client thoroughly. It is better to over-stay than to hang up prematurely.
            - NEVER end a call just because the client spoke in a different language.
            - NEVER end a call because something was unclear, garbled, or hard to understand. Ask the client to repeat themselves.
            - NEVER end a call because the client seems confused, hesitant, or off-topic. Guide them back to the conversation.
            - NEVER end a call because YOU think the conversation is going badly, is unproductive, or has no value. That is not your decision to make.
            - NEVER end a call based on your own assessment of the conversation quality or outcome.
            - The ONLY valid reasons to end a call are:
                1. The client has EXPLICITLY said goodbye, farewell, or clearly stated they want to hang up.
                2. The client is completely unresponsive after AT LEAST 3 separate attempts to re-engage.
            - BEFORE ending any call (even in case 1), you MUST:
                1. Ask "Is there anything else I can help you with?" and receive an explicit "no".
                2. Offer a polite farewell and wait for the client to acknowledge.
            - When in doubt, KEEP THE CALL GOING. Ask if there is anything else you can help with.

            {f"OPERATIONAL GUIDELINES: {self.agent.instructions}." if self.agent.instructions else ""}
            {f"STRATEGY: {self.agent.strategy}." if self.agent.strategy else ""}
            CONTEXT: {context}
        """.strip()

        super().__init__(
            instructions=instructions,
            tools=tools,
        )

        self.opening_message_instructions = f"""
        {f"Open the conversation following these message instructions:\n{self.agent.opening_message}" if self.agent.opening_message else ""}
        """.strip()

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=self.opening_message_instructions, allow_interruptions=False
        )
        # consent = await CollectConsentTask(self.opening_message_instructions, self.chat_ctx)
        # if not consent:
        #     await self.session.generate_reply(instructions="Inform the user that you are unable to proceed and will end the call.")
        #     await self.end_call(status='cancelled', reason='Consent not granted')

    # @function_tool()
    # async def end_call(self, status: str, reason: str, ctx: RunContext):
    #     """
    #     CRITICAL: Use this tool ONLY as an absolute last resort.

    #     This ends the current call permanently. DO NOT use this tool unless these conditions are met:

    #     REQUIRED CONDITIONS:
    #     The customer has explicitly said goodbye, ended the conversation, or hung up
    #     OR these conditions are met(ALL must be true):
    #     1. All customer questions have been fully answered
    #     2. All requested actions/tasks have been completed
    #     3. The customer has confirmed they have no further questions
    #     4. You have offered additional help and the customer declined

    #     NEVER use this if:
    #     - The customer is still talking or asking questions
    #     - You are waiting for information from tools
    #     - The conversation is ongoing
    #     - There is any uncertainty about whether the customer is done

    #     When in doubt, DO NOT end the call. Ask the customer if they need anything else instead.

    #     Args:
    #         status: The call end status (completed, failed, cancelled).
    #         reason: Brief explanation of why the call is ending.
    #     """
    #     logger.info(f"Ending call with status {status} and reason {reason}")
    #     try:
    #         await ctx.wait_for_playout()
    #         self.session.shutdown()
    #     except Exception as e:
    #         raise ToolError(f"Error ending call: {e}")
    #     return {"status": status, "reason": reason}

    def transcription_node(
        self, text: AsyncIterable[str | TimedString], model_settings: ModelSettings
    ) -> (
        AsyncIterable[str | TimedString]
        | Coroutine[Any, Any, AsyncIterable[str | TimedString]]
        | Coroutine[Any, Any, None]
    ):
        """
        A node in the processing pipeline that finalizes transcriptions from text segments.

        This node can be used to adjust or post-process text coming from an LLM (or any other
        source) into a final transcribed form. For instance, you might clean up formatting, fix
        punctuation, or perform any other text transformations here.

        You can override this node to customize post-processing logic according to your needs.

        Args:
            text (AsyncIterable[str | TimedString]): An asynchronous stream of text segments.
            model_settings (ModelSettings): Configuration and parameters for model execution.

        Yields:
            str: Finalized or post-processed text segments.
        """

        async def processed_transcription(
            agent: Agent,
            text: AsyncIterable[str | TimedString],
            model_settings: ModelSettings,
        ) -> AsyncGenerator[str | TimedString, None]:
            """Processes incoming text segments and yields them after logging."""
            # Iterate through incoming text segments
            async for delta in text:
                # logger.debug(
                #     f"Chunk: {delta} ({type(delta)}, thought: {is_thought(str(delta))})"
                # )
                # Add to thoughts if it's a thought
                if is_thought(str(delta)):
                    continue
                # Yield the text segment
                yield delta

        return processed_transcription(self, text, model_settings)


__all__ = ["CallAgent"]
