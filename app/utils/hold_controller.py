"""
Hold controller service
"""

from typing import Optional

from livekit.agents import (
    NOT_GIVEN,
    AgentSession,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
)


class HoldController:
    def __init__(
        self,
        ctx: JobContext,
        session: Optional[AgentSession] = None,
        hold_music: Optional[BackgroundAudioPlayer] = None,
        background_audio: Optional[BackgroundAudioPlayer] = None,
    ):
        """
        Initialize a HoldController instance.

        Args:
            ctx (JobContext): The job context containing room and other metadata.
            session (Optional[AgentSession], optional): The agent session to control audio input. Defaults to None.
            hold_music (Optional[BackgroundAudioPlayer], optional): Custom background audio player for hold music. If not provided, a default player with HOLD_MUSIC is used.
            background_audio (Optional[BackgroundAudioPlayer], optional): Custom background audio player for background audio.
        """
        # Controllables
        self.ctx = ctx
        self.session = None

        # Hold Props
        self.hold = False
        self.hold_music = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.HOLD_MUSIC, volume=1),
        )

        # Background Audio
        self.background_audio = background_audio

    def set_session(self, session: AgentSession):
        self.session = session
        enable = not self.hold
        self.session.input.set_audio_enabled(enable)
        self.session.output.set_audio_enabled(enable)

    async def set_background_audio(self, background_audio: BackgroundAudioPlayer):
        self.background_audio = background_audio
        if self.hold:
            await self.background_audio.aclose()
        else:
            await self.background_audio.start(
                room=self.ctx.room,
                agent_session=self.session or NOT_GIVEN,
            )

    async def start(self):
        # Already holding
        if self.hold:
            return

        # Mute session input audio
        if self.session:
            self.session.input.set_audio_enabled(False)
            self.session.output.set_audio_enabled(False)

        # Stop background audio
        if self.background_audio:
            await self.background_audio.aclose()

        # Start hold music in room
        await self.hold_music.start(room=self.ctx.room)

        # Flag hold state
        self.hold = True

    async def stop(self):
        # Already not holding
        if not self.hold:
            return

        # Unmute session input audio
        if self.session:
            self.session.input.set_audio_enabled(True)
            self.session.output.set_audio_enabled(True)

        # Start background audio
        if self.background_audio:
            await self.background_audio.start(
                room=self.ctx.room,
                agent_session=self.session or NOT_GIVEN,
            )

        # Stop hold music in room
        await self.hold_music.aclose()

        # Flag hold state
        self.hold = False


__all__ = ["HoldController"]
