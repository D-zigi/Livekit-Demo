"""Meeting booking workflow assembled declaratively from a WorkflowSchema."""
from app.models.workflows.nodes_schemas import (
    EndNodeData,
    StartNodeData,
    TaskCompletionTool,
    TaskNodeDataBoolean,
    TaskNodeDataGeneric,
    TaskNodeDataObject,
    TaskResultFieldGeneric,
)
from app.models.workflows.workflow_schema import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowSchema,
)


def _node(id: str, data) -> WorkflowNode:
    return WorkflowNode(id=id, type=data.type, position={"x": 0, "y": 0}, data=data)


MEETING_BOOKING_SCHEMA = WorkflowSchema(
    entry_node_id="start",
    nodes=[
        _node("start", StartNodeData()),
        _node(
            "check_existing_meeting",
            TaskNodeDataBoolean(
                label="check_existing_meeting",
                result_type="boolean",
                instructions=(
                    "Check whether the client already has a meeting scheduled.\n"
                    "If they have one, ask whether they want to keep it or reschedule. "
                    "Make it clear they can only have one meeting at a time.\n"
                    "Call `proceed_with_booking` if there is no existing meeting, or "
                    "if the client wants to reschedule.\n"
                    "Call `keep_existing` if the client wants to keep their current meeting."
                ),
                completion_tools=[
                    TaskCompletionTool(
                        id="proceed_with_booking",
                        name="proceed_with_booking",
                        description="No existing meeting, or the client wants to reschedule.",
                        value=True,
                    ),
                    TaskCompletionTool(
                        id="keep_existing",
                        name="keep_existing",
                        description="The client wants to keep their existing meeting.",
                        value=False,
                    ),
                ],
            ),
        ),
        _node(
            "collect_preferred_time",
            TaskNodeDataObject(
                label="collect_preferred_time",
                result_type="object",
                instructions=(
                    "Collect the client's preferred meeting date and time.\n"
                    "Meetings are available Monday-Friday, 9 AM to 5 PM Central Time.\n"
                    "Call `time_provided` once you have a valid date and time."
                ),
                result_fields=[
                    TaskResultFieldGeneric(
                        id="date",
                        name="date",
                        type="string",
                        required=True,
                        description="Preferred date in YYYY-MM-DD format.",
                    ),
                    TaskResultFieldGeneric(
                        id="time",
                        name="time",
                        type="string",
                        required=True,
                        description="Preferred time in HH:MM 24-hour format.",
                    ),
                ],
                completion_tools=[
                    TaskCompletionTool(
                        id="time_provided",
                        name="time_provided",
                        description="Use when the client has provided a valid preferred date and time.",
                    ),
                ],
            ),
        ),
        _node(
            "get_email",
            TaskNodeDataGeneric(
                label="get_email",
                result_type="string",
                instructions=(
                    "Collect a valid email address from the client for the meeting confirmation.\n"
                    "Call `email_given` once the client has provided a valid email."
                ),
                completion_tools=[
                    TaskCompletionTool(
                        id="email_given",
                        name="email_given",
                        description="Use when the client has provided a valid email address.",
                    ),
                ],
            ),
        ),
        _node(
            "meeting_booking",
            TaskNodeDataObject(
                label="meeting_booking",
                result_type="object",
                instructions=(
                    "Complete the meeting booking end-to-end:\n"
                    "1. Create the calendar event for the previously collected date and time.\n"
                    "2. Send a confirmation email via Gmail.\n"
                    "3. Send a WhatsApp or SMS confirmation message.\n"
                    "4. Confirm with the client that the calendar invite, email, and message arrived. "
                    "Iterate (resend, verify contact details) if anything is missing.\n"
                    "Call `booking_complete` only after every step has succeeded and the client has confirmed receipt."
                ),
                result_fields=[
                    TaskResultFieldGeneric(
                        id="event_id",
                        name="event_id",
                        type="string",
                        required=True,
                        description="The calendar event ID.",
                    ),
                    TaskResultFieldGeneric(
                        id="email",
                        name="email",
                        type="string",
                        required=True,
                        description="Email address the confirmation was sent to.",
                    ),
                    TaskResultFieldGeneric(
                        id="phone_number",
                        name="phone_number",
                        type="string",
                        required=True,
                        description="Phone number the confirmation message was sent to.",
                    ),
                ],
                completion_tools=[
                    TaskCompletionTool(
                        id="booking_complete",
                        name="booking_complete",
                        description="Use after the calendar event is created and the client has confirmed receipt of email and message.",
                    ),
                ],
            ),
        ),
        _node(
            "end",
            EndNodeData(closing_message="Thank the client warmly and say goodbye."),
        ),
    ],
    edges=[
        WorkflowEdge(
            id="start__check",
            source="start",
            target="check_existing_meeting",
            label="",
            kind="session-start",
        ),
        WorkflowEdge(
            id="check__collect",
            source="check_existing_meeting",
            target="collect_preferred_time",
            label="proceed",
            kind="task-result",
            task_result_key=True,
        ),
        WorkflowEdge(
            id="check__end",
            source="check_existing_meeting",
            target="end",
            label="keep existing",
            kind="task-result",
            task_result_key=False,
        ),
        WorkflowEdge(
            id="collect__email",
            source="collect_preferred_time",
            target="get_email",
            label="",
            kind="task-run",
        ),
        WorkflowEdge(
            id="email__booking",
            source="get_email",
            target="meeting_booking",
            label="",
            kind="task-run",
        ),
        WorkflowEdge(
            id="booking__end",
            source="meeting_booking",
            target="end",
            label="",
            kind="task-run",
        ),
    ],
)


__all__ = ["MEETING_BOOKING_SCHEMA"]
