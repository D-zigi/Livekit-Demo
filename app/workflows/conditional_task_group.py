from typing import Any, Callable, Coroutine

from livekit.agents import NOT_GIVEN, AgentTask, NotGivenOr, llm
from livekit.agents.beta.workflows.task_group import (
    _OutOfScopeError,
    TaskCompletedEvent,
    TaskGroup,
    TaskGroupResult
)

class ConditionalTaskGroup(TaskGroup):
    """
    A TaskGroup that conditionally executes tasks based on the results of previous tasks.
    The LLM can regress to previously completed tasks by referencing their task IDs in the task description.
    """
    def __init__(
        self,
        *,
        summarize_chat_ctx: bool = True,
        return_exceptions: bool = False,
        chat_ctx: NotGivenOr[llm.ChatContext] = NOT_GIVEN,
        on_task_completed: Callable[[TaskCompletedEvent], Coroutine[None, None, None]]
        | None = None,
    ):
        super().__init__(
            summarize_chat_ctx=summarize_chat_ctx,
            return_exceptions=return_exceptions,
            chat_ctx=chat_ctx,
            on_task_completed=on_task_completed
        )
        self._gates: dict[str, Callable[[dict[str, Any]], bool]] = {}

    def add(
        self,
        task_factory: Callable[[], AgentTask],
        *,
        id: str,
        description: str,
        gate: Callable[[dict[str, Any]], bool] | None = None,
    ):
        """Upserts an AgentTask to the TaskGroup.

        Args:
            task_factory (Callable[[], AgentTask]): A factory function that creates an AgentTask.
            gate (Callable[[dict[str, Any]], bool]): A function that determines whether the task should be executed based on the results of previous tasks.
            id (str): A unique identifier for the task.
            description (str): A description of the task. This can include references to previous tasks by their IDs to allow for regression.
        """
        super().add(task_factory=task_factory, id=id, description=description)
        self._gates[id] = gate or (lambda _: True)
        return self

    async def on_enter(self) -> None:
        task_stack = list(self._registered_factories.keys())
        task_results: dict[str, Any] = {}

        while len(task_stack) > 0:
            task_id = task_stack.pop(0)
            if not self._gates[task_id](task_results):
                continue
            factory_info = self._registered_factories[task_id]

            self._current_task = factory_info.task_factory()

            shared_chat_ctx = self.chat_ctx.copy()
            await self._current_task.update_chat_ctx(shared_chat_ctx)

            if out_of_scope_tool := self._build_out_of_scope_tool(active_task_id=task_id):
                current_tools = self._current_task.tools
                current_tools.append(out_of_scope_tool)
                await self._current_task.update_tools(current_tools)

            try:
                self._visited_tasks.add(task_id)
                res = await self._current_task

                # AgentTask handoff merges omit function calls. Re-merge the completed
                # task context so task-group summarization can incorporate tool results.
                self._chat_ctx.merge(
                    self._current_task.chat_ctx.copy(),
                    exclude_instructions=True,
                )

                task_results[task_id] = res

                if self._task_completed_callback is not None:
                    await self._task_completed_callback(
                        TaskCompletedEvent(
                            agent_task=self._current_task, task_id=task_id, result=res
                        )
                    )
            except _OutOfScopeError as e:
                task_stack.insert(0, task_id)
                for task_id in reversed(e.target_task_ids):
                    task_stack.insert(0, task_id)
                continue
            except Exception as e:
                if self._return_exceptions:
                    task_results[task_id] = e
                    continue
                else:
                    self.complete(e)
                    return

        if self._summarize_chat_ctx:
            try:
                assert isinstance(self.session.llm, llm.LLM), (
                    "llm must be a LLM instance to summarize the chat_ctx"
                )

                # when a task is done, the chat_ctx is going to be merged with the "caller" chat_ctx
                # enabling summarization will result on only one ChatMessage added.
                # keep every item to allow summarization to be more action-aware.
                summarized_chat_ctx = await self.chat_ctx.copy(
                    exclude_instructions=False,
                    exclude_handoff=False,
                    exclude_config_update=False,
                    exclude_empty_message=False,
                    exclude_function_call=False,
                )._summarize(llm_v=self.session.llm, keep_last_turns=0)

                await self.update_chat_ctx(summarized_chat_ctx)
            except Exception as e:
                self.complete(e)
                return

        self.complete(TaskGroupResult(task_results=task_results))
