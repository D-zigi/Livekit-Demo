from livekit.agents import AgentSession, AgentTask

from app.models.workflows.nodes_schemas import SayNodeData


def build_say_task(data: SayNodeData, speaker_session: AgentSession | None = None) -> type[AgentTask]:
    class SayTask(AgentTask[None]):
        async def on_enter(self) -> None:
            session = self.session
            if speaker_session is not None:
                session = speaker_session
            await session.generate_reply(
                instructions=data.instructions
            )
            self.complete(None)
    return SayTask


__all__ = ["build_say_task"]
