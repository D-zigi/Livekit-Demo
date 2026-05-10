from livekit.agents import AgentTask

from app.models.workflows.nodes_schemas import EndNodeData


def build_end_task(data: EndNodeData) -> type[AgentTask]:
    class EndTask(AgentTask[None]):
        async def on_enter(self) -> None:
            await self.session.generate_reply(
                instructions=data.closing_message
                or "The workflow has ended. You can summarize the conversation and next steps for the client if needed and say goodbye."
            )
            self.session.on("close", lambda: self.complete(None))
    return EndTask

__all__ = ["build_end_task"]
