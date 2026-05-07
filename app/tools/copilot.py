from livekit.agents import AgentSession, RunContext, llm


def build_delegate_to_agent_tool(session: AgentSession):
    async def delegate_to_agent(
        context: RunContext,
        task_description: str,
    ):
        """
        Delegates a task to an agent.
        Args:
            task_description: A description of the task to delegate to the agent.
        returns: The speech handle or the text response.
        """
        if session.llm is None:
            raise ValueError("LLM model is not configured for the session.")

        if isinstance(session.llm, llm.RealtimeModel):
            speech = await session.generate_reply(
                instructions=f"Execute the task: {task_description}",
            )
            return speech
        elif isinstance(session.llm, llm.LLM):
            chat_ctx = session._chat_ctx.copy()
            chat_ctx.add_message(
                role="user",
                content=f"Execute the task: {task_description}"
            )
            response_text = ""
            async with session.llm.chat(chat_ctx=chat_ctx) as stream:
                async for chunk in stream:
                    if chunk.delta and chunk.delta.content:
                        response_text += chunk.delta.content
            return response_text
    return delegate_to_agent


__all__ = [
    "build_delegate_to_agent_tool",
]
