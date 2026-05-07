"""
Call orchestrator module for managing the full lifecycle of an agent call session.
"""

import asyncio
import logging
from datetime import datetime, timezone

from httpx import HTTPError
from livekit.agents import AgentSession, AudioConfig, BuiltinAudioClip, JobContext
from livekit.agents.voice.room_io.types import (
    AudioInputOptions,
    RoomOptions,
    TextOutputOptions,
)
from livekit.plugins import noise_cancellation
from pydantic import ValidationError

from app.api.call import end_call, get_call, start_call
from app.models.call import CallEnd
from app.models.call_data import CallData
from app.services.agent import CallAgent
from app.services.call_data import get_call_data, get_call_details
from app.services.audio_controller import AudioController
from app.services.session import create_call_session
from app.utils.egress import start_audio_recording
from app.utils.lifecycle import shutdown

logger = logging.getLogger(__name__)


class CallOrchestrator:
    """
    Orchestrates the full lifecycle of an agent call session.

    Use the async factory method `create()` to instantiate — this ensures
    all dependencies are fully initialized before use.
    """

    def __init__(
        self,
        ctx: JobContext,
        call_data: CallData,
        session: AgentSession,
        agent: CallAgent,
        audio_controller: AudioController,
        call_logs_queue: asyncio.Queue,
    ):
        self.ctx = ctx
        self.call_data = call_data
        self.session = session
        self.agent = agent
        self.audio_controller = audio_controller
        self._call_logs_queue = call_logs_queue
        self.call_details = get_call_details(ctx)

    @classmethod
    async def create(cls, ctx: JobContext) -> "CallOrchestrator | None":
        """
        Async factory method. Builds and returns a fully initialized
        CallOrchestrator, or returns None (after shutting down) on failure.
        """
        # Create call logs queue
        call_logs_queue: asyncio.Queue = asyncio.Queue()

        # Start audio controller and ensure it stops on shutdown
        audio_controller = AudioController(
            ctx=ctx,
            thinking_sound=[
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.4, probability=0.5),
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.2, probability=0.5),
            ]
        )
        await audio_controller.start()
        ctx.add_shutdown_callback(audio_controller.close)
        # Start hold music for inbound calls
        if get_call_details(ctx).call_direction == "inbound":
            await audio_controller.hold()

        # Get call data
        call_data = await get_call_data(ctx)
        if not call_data:
            await shutdown(ctx=ctx, reason="Failed to get call data")
            return None

        # Initialize ambient sound if enabled
        if call_data.background_audio_enabled:
            audio_controller.ambient_sound = AudioConfig("app/resources/office-ambience.ogg", volume=0.6)

        # Create call session
        session = await create_call_session(ctx, call_data, call_logs_queue, audio_controller)
        if not session:
            await shutdown(ctx=ctx, reason="Failed to create agent session")
            return None

        # Create agent
        agent = CallAgent(call_data, call_logs_queue, audio_controller)

        orchestrator = cls(ctx, call_data, session, agent, audio_controller, call_logs_queue)

        # Ensure call end is handled on shutdown
        ctx.add_shutdown_callback(orchestrator._shutdown_end_call)
        return orchestrator

    async def kickoff(self) -> None:
        """Start recording, start the agent session, and flag call as started in DB."""
        # Start call recording
        recording = await start_audio_recording(
            self.ctx, self.call_data.business_id, self.call_data.call.get_origin()[0]
        )
        if not recording:
            self.ctx.shutdown("Failed to start recording")
            return

        # Start the session with the agent
        await self.session.start(
            agent=self.agent,
            room=self.ctx.room,
            room_options=RoomOptions(
                audio_input=AudioInputOptions(noise_cancellation=noise_cancellation.BVC()),
                text_output=TextOutputOptions(sync_transcription=True),
                close_on_disconnect=True,
                delete_room_on_close=True,
            ),
        )

        # Flag call as started in DB
        await start_call(
            business_id=self.call_data.business_id,
            call_id=self.call_data.call.id,
            room_name=self.ctx.room.name,
            started_at=(
                datetime.fromtimestamp(
                    recording.started_at / 1_000_000_000, tz=timezone.utc
                ).isoformat()
            ),
        )

    async def _shutdown_end_call(self) -> None:
        # NOTE: Give the call a chance to terminate gracefully before forcefully terminating it
        await asyncio.sleep(5)

        try:
            try:
                call = await get_call(self.call_data.business_id, self.call_data.call.id)
                if call:
                    CallEnd.model_validate({"id": call.id, "status": call.status})
            except ValidationError:
                await end_call(
                    business_id=self.call_data.business_id,
                    data=CallEnd(id=self.call_data.call.id, status="completed")
                )
        except HTTPError as e:
            logger.error(f"Failed to end call: {e}")
