import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, List, Optional

from livekit.agents import (
    Agent,
    AgentSession,
    ConversationItemAddedEvent,
    ToolError,
    function_tool,
    llm,
)

from app.workflows.meeting_booking import MeetingBookingWorkflow

logger = logging.getLogger(__name__)

# Proposals expire if the customer's conversation moves on without confirming.
# Tunable. Short enough to catch "I changed my mind" drift, long enough to
# accommodate the main agent reading the proposal back and the customer answering.
PROPOSAL_TTL_SECONDS = 60.0


@dataclass
class ProposedAction:
    id: str
    action: str  # name of the underlying mutating tool to invoke on commit
    params: dict[str, Any]
    summary: str
    proposed_at: float


class CopilotAgent(Agent):
    """Silent copilot. Runs tools and briefs the main voice agent through a typed surface."""

    def __init__(
        self,
        main_agent: Agent,
        main_session: AgentSession,
        context: Optional[str] = None,
        tools: Optional[List[llm.Tool | llm.Toolset]] = None,
    ):
        self._instructions = f"""
        You are a silent copilot for a voice agent. The customer cannot hear you;
        the main agent can. You see the same conversation and own the tool surface.
        DO NOT speak to the customer. Your only outputs are tool calls.

        Look. Think. Act:
        - When something needs a tool, run it and route the outcome through the
          typed briefing tools below. Never echo the customer.
        - If there is nothing new to add, stay silent.

        TOOL SURFACE — pick the right channel:

        1. `inform_agent(note)` → SILENT narrative context the main agent should be
           aware of but doesn't need to verbalize. Examples: "customer sounds frustrated",
           "we're nearing the end of available slots, wrap up soon".

        2. `provide_tool_result(tool_name, result)` → AUTHORITATIVE result of a
           READ-ONLY tool the customer is waiting on. Use immediately after running
           any non-mutating tool (search, lookup, check availability, list, fetch).
           The main agent will speak this. The result must be a faithful summary —
           never soften, never embellish.

        3. `propose_action(action, params, summary)` → REGISTER a mutating action
           you intend to perform. DOES NOT execute it. The main agent will read the
           summary back to the customer for explicit confirmation. Returns a
           proposal_id you'll need for commit.

        4. `commit_action(proposal_id)` → CONFIRM and execute a previously proposed
           action. Only call after you see the customer's explicit verbal "yes" in
           the transcript. If the customer corrected ANY detail, do NOT commit —
           call `propose_action` again with the corrected params.

        5. `change_goal(goal)` → BEHAVIORAL pivot for the main agent ("we're now
           rescheduling, not booking"). Not for facts. Facts go through #2.

        HARD RULES:
        - You may NEVER call a mutating tool (create_*, book_*, schedule_*, send_*,
          update_*, delete_*, cancel_*) directly. Mutating tools are only reachable
          through the propose → commit cycle. `commit_action` will refuse if there is
          no matching pending proposal.
        - When the customer's transcript contradicts a pending proposal (e.g., they
          said "actually Monday, not Sunday"), discard the stale proposal by calling
          `propose_action` again with the corrected details. Do not commit on stale data.

        {context or ""}
        """.strip()

        self.main_agent = main_agent
        self.main_session = main_session
        self._pending_proposals: dict[str, ProposedAction] = {}

        super().__init__(instructions=self._instructions, tools=tools)

        self._setup_listeners()

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    def _setup_listeners(self) -> None:
        @self.main_session.on("conversation_item_added")
        def _on_conversation_item_added(event: ConversationItemAddedEvent) -> None:
            chat_message = event.item
            if not isinstance(chat_message, llm.ChatMessage) or chat_message.role != "assistant":
                return
            ctx = self.chat_ctx.copy()
            ctx.add_message(
                role="system",
                content=f"Main agent said:\n{chat_message.text_content}",
            )
            logger.warning(f"Main agent said:\n{chat_message.text_content}")
            asyncio.create_task(self.update_chat_ctx(ctx))

    async def _push_to_main(self, content: str, *, speak: bool) -> None:
        """Append a user-role turn to the main agent's chat_ctx, optionally triggering speech."""
        new_ctx = self.main_agent.chat_ctx.copy()
        new_ctx.add_message(role="user", content=content)
        await self.main_agent.update_chat_ctx(new_ctx)

        if not speak:
            return
        if self.main_session.user_state == "speaking":
            logger.info("Suppressing generate_reply: customer is speaking.")
            return
        self.main_session.generate_reply()  # fire-and-forget

    def _gc_proposals(self) -> None:
        now = time.monotonic()
        expired = [
            pid for pid, p in self._pending_proposals.items()
            if now - p.proposed_at > PROPOSAL_TTL_SECONDS
        ]
        for pid in expired:
            logger.info(f"Proposal {pid} expired (>{PROPOSAL_TTL_SECONDS}s).")
            self._pending_proposals.pop(pid, None)

    # -------------------------------------------------------------------------
    # Tools — typed briefing surface
    # -------------------------------------------------------------------------

    @function_tool()
    async def inform_agent(self, note: str) -> str:
        """Soft narrative context the main agent should be aware of but doesn't
        need to verbalize. Silent — does not trigger speech.

        Args:
            note: Short observation about the conversation or customer state.
        """
        logger.info(f"[inform_agent] {note}")
        await self._push_to_main(f"<copilot_note>\n{note}\n</copilot_note>", speak=False)
        return "Note delivered."

    @function_tool()
    async def provide_tool_result(self, tool_name: str, result: str) -> str:
        """Deliver an authoritative result of a READ-ONLY tool the customer is
        waiting on. Triggers the main agent to speak (unless the customer is
        mid-utterance, in which case it lands silently and is picked up on the
        next natural turn).

        Args:
            tool_name: Name of the read-only tool whose result this is.
            result: Faithful, concise summary the main agent will read aloud.
        """
        logger.info(f"[provide_tool_result] {tool_name}: {result}")
        composed = (
            f'<copilot_briefing tool="{tool_name}">\n'
            f"{result}\n"
            f"</copilot_briefing>"
        )
        await self._push_to_main(composed, speak=True)
        return f"Result for '{tool_name}' delivered to main agent."

    @function_tool()
    async def propose_action(
        self,
        action: str,
        params: str,
        summary: str,
    ) -> str:
        """Register a mutating action you INTEND to perform. Does NOT execute it.
        The main agent will read `summary` back to the customer for explicit
        confirmation. Returns a proposal_id you'll need to pass to commit_action.

        Args:
            action: Name of the underlying mutating tool you intend to call on commit.
            params: JSON-serialized arguments you will pass to that tool when committing. Example: '{"date": "2025-01-15", "time": "14:00"}'.
            summary: Concise human-readable description for the customer to confirm.
        """
        import json
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError as e:
            raise ToolError(f"params must be valid JSON: {e}")
        self._gc_proposals()
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        self._pending_proposals[proposal_id] = ProposedAction(
            id=proposal_id,
            action=action,
            params=parsed_params,
            summary=summary,
            proposed_at=time.monotonic(),
        )
        logger.info(f"[propose_action] {proposal_id} action={action} params={params}")
        composed = (
            f'<copilot_proposal id="{proposal_id}" action="{action}">\n'
            f"{summary}\n"
            f"</copilot_proposal>"
        )
        await self._push_to_main(composed, speak=True)
        return (
            f"Proposal {proposal_id} registered. Wait for the customer's explicit "
            f"confirmation in the transcript, then call commit_action('{proposal_id}'). "
            f"If they correct any detail, propose again instead."
        )

    @function_tool()
    async def commit_action(self, proposal_id: str) -> str:
        """Confirm and authorize execution of a previously proposed action. The
        customer must have given explicit verbal confirmation in the transcript
        since the proposal was made.

        Args:
            proposal_id: The id returned by `propose_action`.
        """
        self._gc_proposals()
        proposal = self._pending_proposals.pop(proposal_id, None)
        if proposal is None:
            raise ToolError(
                f"No pending proposal with id '{proposal_id}'. Either it was never "
                "proposed, it expired, or you already committed it. Re-propose with "
                "fresh details if the customer still wants to proceed."
            )
        logger.info(
            f"[commit_action] {proposal_id} action={proposal.action} params={proposal.params}"
        )
        return (
            f"Proposal {proposal_id} confirmed. You may now invoke `{proposal.action}` "
            f"with these params: {proposal.params}. Report the outcome via "
            f"provide_tool_result once it returns."
        )

    @function_tool()
    async def change_goal(self, goal: str) -> str:
        """Update the main agent's behavioral focus. Use only for genuine workflow
        pivots ("switching from booking to rescheduling"), NOT for facts. Facts
        go through provide_tool_result.

        Args:
            goal: The new behavioral directive for the main agent.
        """
        logger.info(f"[change_goal] {goal}")
        await self.main_agent.update_instructions(f"UPDATED GOAL:\n{goal}\n")
        return f"Goal updated: {goal}"

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def on_enter(self) -> None:
        result = await MeetingBookingWorkflow(
            chat_ctx=self.chat_ctx,
            extra_instructions=self._instructions,
            extra_tools=self.tools,
        )
        logger.info(f"Workflow result: {result}")


__all__ = ["CopilotAgent", "ProposedAction"]
