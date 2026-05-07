"""
Consent and compliance tasks for the voice agent.
"""
from livekit.agents import AgentTask, function_tool, ChatContext

class CollectConsentTask(AgentTask[bool]):
    def __init__(self, extra_instructions: str, chat_ctx: ChatContext):
        super().__init__(
            instructions="""
            Ask for recording consent and get a clear yes or no answer.
            Be polite and professional.
            """ + extra_instructions,
            chat_ctx=chat_ctx
        )

    # called when task is started
    async def on_enter(self) -> None:
        print("CollectConsentTask started")
        await self.session.generate_reply(
            instructions="""
            Briefly introduce yourself, then ask for permission to record the call for quality assurance and training purposes.
            Make it clear that they can decline.
            """
        )

    @function_tool
    async def consent_given(self) -> None:
        """Use this when the user gives consent to record."""
        self.complete(True)

    @function_tool
    async def consent_denied(self) -> None:
        """Use this when the user denies consent to record."""
        self.complete(False)

__all__ = [
    "CollectConsentTask",
]
