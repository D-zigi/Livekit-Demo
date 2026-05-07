"""
Session service module for handling custom agents sessions.
"""

import asyncio
import logging

from google.genai.types import (
    AutomaticActivityDetection,
    Behavior,
    FunctionResponseScheduling,
    RealtimeInputConfig,
    StartSensitivity,
    ThinkingConfig,
    ThinkingLevel,
)
from livekit.agents import NOT_GIVEN, AgentSession, JobContext
from livekit.plugins import google

from app.core.config import settings
from app.models.agent import GeminiLiveLanguageMap
from app.models.call_data import CallData
from app.models.call_log import CallLogCreate
from app.services.call_logs import call_logs_queue_worker
from app.services.audio_controller import AudioController
from app.services.user_state_controller import UserStateController
from app.utils.lifecycle import shutdown
from app.utils.session import (
    handle_agent_state_changed,
    handle_call_end,
    handle_conversation_item,
    handle_function_tools_executed,
)

logger = logging.getLogger(__name__)


# Create Call Session
async def create_call_session(
    ctx: JobContext,
    call_data: CallData,
    call_logs_queue: asyncio.Queue[CallLogCreate],
    audio_controller: AudioController,
):
    """
    Create a new call session with custom configurations
    and context provided by the call.

    args:
        call_data: CallData - The call data object containing details for the session.
    """
    # Extracting call data
    call = call_data.call

    # Extracting call details
    agent = call.agents
    if not agent:
        await shutdown(ctx=ctx, reason="Agent not found for the call")
        return

    # Google Realtime Model
    google_realtime_model = google.realtime.RealtimeModel(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        model=agent.model,
        voice=agent.voice_model,
        language=(
            agent.language if agent.language in GeminiLiveLanguageMap else NOT_GIVEN
        ),
        temperature=agent.temperature,
        # realtime_input_config=RealtimeInputConfig(
        #     automatic_activity_detection=AutomaticActivityDetection(
        #         start_of_speech_sensitivity=StartSensitivity.START_SENSITIVITY_LOW
        #     )
        # ),
        # thinking_config=ThinkingConfig(
        #     include_thoughts=True,
        #     thinking_budget=2048,
        #     # thinking_level=ThinkingLevel.LOW,
        # ),
        # tool_behavior=Behavior.NON_BLOCKING,
        # tool_response_scheduling=FunctionResponseScheduling.WHEN_IDLE,
        # enable_affective_dialog=True,
        # proactivity=True,
    )

    # Realtime Agent Session
    session = AgentSession(
        llm=google_realtime_model,
        use_tts_aligned_transcript=True,
        preemptive_generation=True,
        allow_interruptions=True,
        user_away_timeout=12.5,
    )

    # Set Session in audio controller
    await audio_controller.set_session(session)

    # User State Controller
    user_state_controller = UserStateController(session=session)

    # Ensure user state controller cleans up on shutdown
    async def close_user_state_controller():
        user_state_controller.close()

    ctx.add_shutdown_callback(close_user_state_controller)

    # Handle call logs worker
    logs_worker_task = asyncio.create_task(
        call_logs_queue_worker(
            business_id=call_data.business_id,
            call_logs_queue=call_logs_queue,
        )
    )

    # Ensure logs worker is canceled on shutdown
    async def cancel_logs_worker():
        logs_worker_task.cancel()
        try:
            await logs_worker_task
        except asyncio.CancelledError:
            pass

    ctx.add_shutdown_callback(cancel_logs_worker)

    # Event Handlers
    session.on(  # User State Changed
        "user_state_changed", user_state_controller.handle_user_state_changed
    )

    session.on(  # Agent State Changed
        "agent_state_changed",
        lambda event: asyncio.create_task(
            handle_agent_state_changed(
                ctx=ctx,
                session=session,
                event=event,
                audio_controller=audio_controller,
            )
        ),
    )

    session.on(  # Conversation Item Added
        "conversation_item_added",
        lambda event: handle_conversation_item(
            event=event,
            call=call,
            call_logs_queue=call_logs_queue,
        ),
    )

    session.on( # Agent State Changed
        "function_tools_executed",
        lambda event: handle_function_tools_executed(
            event=event,
            call=call,
            call_logs_queue=call_logs_queue,
        )
    )

    session.on(  # Call Ended
        "close", lambda event: asyncio.create_task(handle_call_end(ctx, call))
    )

    return session
