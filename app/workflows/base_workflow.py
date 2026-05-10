from typing import Any, Callable, Coroutine, List

from livekit.agents import NOT_GIVEN, AgentSession, ChatContext, NotGivenOr, llm
from livekit.agents.beta.workflows import TaskCompletedEvent

from app.utils.dag import DirectedAcyclicGraph

from app.models.workflows.nodes_schemas import SayNodeData, EndNodeData, StartNodeData
from app.models.workflows.workflow_schema import WorkflowEdge, WorkflowNode

from app.workflows.conditional_task_group import ConditionalTaskGroup
from app.workflows.nodes import build_task, build_say_task, build_end_task


class Workflow:
    """Workflow for booking a meeting."""
    def __init__(
        self,
        tasks: List[WorkflowNode],
        edges: List[WorkflowEdge],
        speaker_session: AgentSession | None = None,
        chat_ctx: NotGivenOr[ChatContext] = NOT_GIVEN,
        extra_tools: List[llm.Tool | llm.Toolset] | None = None,
        extra_instructions: str = "",
        on_task_completed: Callable[[TaskCompletedEvent], Coroutine[None, None, None]] | None = None,
        summarize_chat_ctx: bool = True,
    ):
        # Construct the workflow graph and sort tasks topologically
        self.tasks = tasks
        self.edges = edges
        self._setup_flow()

        self.speaker_session = speaker_session
        self.extra_tools = extra_tools or []
        self.extra_instructions = extra_instructions

        self.task_group = ConditionalTaskGroup(
            chat_ctx=chat_ctx,
            on_task_completed=on_task_completed,
            return_exceptions=False,
            summarize_chat_ctx=summarize_chat_ctx,
        )
        self._setup_tasks()

    def __await__(self):
        return self.task_group.__await__()

    def _setup_flow(self):
        self.flow = DirectedAcyclicGraph(nodes=[task.id for task in self.tasks])
        for edge in self.edges:
            self.flow.add_edge(edge.source, edge.target)

        self.sorted_tasks_ids = self.flow.topo_sort()
        self.tasks = [
            task
            for task in self.tasks
            if task.id in self.sorted_tasks_ids
        ]

    def _build_gate(self, task_id: str) -> Callable[[dict[str, Any]], bool]:
        incoming = [e for e in self.edges if e.target == task_id]
        if len(incoming) == 0:
            return lambda _: True

        def edge_fires(edge: WorkflowEdge, results: dict[str, Any]) -> bool:
            if edge.source not in results:
                return False
            if edge.kind == "task-result" and edge.task_result_key is not None:
                return results[edge.source] == edge.task_result_key.value
            return True

        return lambda results: any(edge_fires(e, results) for e in incoming)

    def _setup_tasks(self):
        for task in self.tasks:
            data = task.data
            if isinstance(data, SayNodeData):
                task_cls = build_say_task(data, self.speaker_session)
            elif isinstance(data, EndNodeData):
                task_cls = build_end_task(data)
            elif isinstance(data, StartNodeData):
                continue
            else:
                task_cls = build_task(data)

            self.task_group.add(
                task_factory=lambda cls=task_cls: cls(instructions="*empty*"),
                id=task.id,
                description=getattr(task.data, "instructions", "") + self.extra_instructions,
                gate=self._build_gate(task.id),
            )


__all__ = ["Workflow"]
