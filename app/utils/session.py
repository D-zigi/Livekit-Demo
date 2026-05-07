"""
Session service utilities for managing call sessions.
"""
import json
import logging
from typing import Optional

from livekit.agents import (
    AgentSession,
    FunctionToolsExecutedEvent,
    JobContext,
    AgentStateChangedEvent
)

from app.utils.hold_controller import HoldController

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Event Handlers
async def handle_agent_state_changed(
    ctx: JobContext,
    session: AgentSession,
    event: AgentStateChangedEvent,
    hold_controller: Optional[HoldController] = None,
):
    logger.debug(f"{event.old_state} -> {event.new_state}")
    if event.new_state == "speaking":
        if hold_controller:
            await hold_controller.stop()

def handle_function_tools_executed(
    event: FunctionToolsExecutedEvent,
):
    # Extract event data
    function_calls = event.function_calls
    function_call_outputs = event.function_call_outputs

    # Create call logs with function calls
    for function_call in function_calls:
        logger.debug(
            f"""{function_call.id} - {function_call.name} ({function_call.type}):
            {json.loads(function_call.arguments)}
            {function_call.extra}
            """
        )

    # Create call logs with function call outputs
    for function_call_output in function_call_outputs:
        logger.debug(
            f"""{function_call_output.id} - {function_call_output.name} ({function_call_output.type}):
            {json.loads(function_call_output.output)}
            {function_call_output.is_error}
            """
        ) if function_call_output else None
