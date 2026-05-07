from typing import Callable, Coroutine, List

from livekit.agents import NOT_GIVEN, ChatContext, NotGivenOr, llm
from livekit.agents.beta.workflows import TaskCompletedEvent, TaskGroup

from .tasks.collect_data import GetEmailTask
from .tasks.meeting_booking import (
    CheckExistingMeetingTask,
    CollectPreferredTimeTask,
    MeetingBookingTask,
)


class MeetingBookingWorkflow:
    """Workflow for booking a meeting."""

    def __init__(
        self,
        chat_ctx: NotGivenOr[ChatContext] = NOT_GIVEN,
        extra_tools: List[llm.Tool | llm.Toolset] | None = None,
        extra_instructions: str = "",
        on_task_completed: Callable[[TaskCompletedEvent], Coroutine[None, None, None]] | None = None,
        summarize_chat_ctx: bool = True,
    ):
        self.extra_tools = extra_tools or []
        self.extra_instructions = extra_instructions

        self.task_group = TaskGroup(
            chat_ctx=chat_ctx,
            on_task_completed=on_task_completed,
            return_exceptions=False,
            summarize_chat_ctx=summarize_chat_ctx,
        )

        self._setup_tasks()

    def __await__(self):
        return self.task_group.__await__()

    def _setup_tasks(self):
        self.task_group.add(
            lambda: CheckExistingMeetingTask(
                extra_instructions=self.extra_instructions,
                tools=self.extra_tools,
            ),
            id="check_existing_meeting",
            description=CheckExistingMeetingTask.__doc__ or "",
        )
        self.task_group.add(
            lambda: CollectPreferredTimeTask(
                extra_instructions=self.extra_instructions,
                tools=self.extra_tools,
            ),
            id="collect_preferred_time",
            description=CollectPreferredTimeTask.__doc__ or "",
        )
        self.task_group.add(
            lambda: GetEmailTask(
                extra_instructions=self.extra_instructions,
                tools=self.extra_tools,
            ),
            id="get_email",
            description=GetEmailTask.__doc__ or "",
        )
        self.task_group.add(
            lambda: MeetingBookingTask(
                extra_instructions=self.extra_instructions,
                tools=self.extra_tools,
            ),
            id="meeting_booking",
            description=MeetingBookingTask.__doc__ or "",
        )


__all__ = ["MeetingBookingWorkflow"]
