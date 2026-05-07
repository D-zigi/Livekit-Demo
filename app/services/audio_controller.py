"""
Audio controller service
"""

import logging
from typing import Optional

from livekit.agents import (
    AgentSession,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    NotGivenOr,
    PlayHandle,
)
from livekit.agents.voice.background_audio import AudioSource

logger = logging.getLogger(__name__)

STREAM_TIMEOUT_MS = 2000

class AudioController:
    """
    Audio controller service
    """
    def __init__(
        self,
        ctx: JobContext,
        session: Optional[AgentSession] = None,
        hold_sound: NotGivenOr[AudioSource | AudioConfig | list[AudioConfig] | None] = None,
        thinking_sound: NotGivenOr[AudioSource | AudioConfig | list[AudioConfig] | None] = None,
        ambient_sound: NotGivenOr[AudioSource | AudioConfig | list[AudioConfig] | None] = None,
    ):
        """
        Initialize a AudioController instance.

        Args:
            ctx (JobContext): The job context containing room and other metadata.
            session (Optional[AgentSession], optional): The agent session to control audio input. Defaults to None.
            hold_sound (Optional[AudioConfig], optional): Custom background audio player for hold music. If not provided, a default player with HOLD_MUSIC is used.
            thinking_sound (Optional[AudioConfig], optional): Custom background audio player for thinking sound.
            ambient_sound (Optional[AudioConfig], optional): Custom background audio player for ambient sound.
        """
        # Controllables
        self.ctx = ctx
        self.session = session

        # Audio Player
        self.thinking_sound = thinking_sound
        self.player = BackgroundAudioPlayer(
            thinking_sound=self.thinking_sound,
            stream_timeout_ms=STREAM_TIMEOUT_MS,
        )
        self._player_started = False

        # Hold Props
        self.on_hold = False
        self.hold_sound = hold_sound or AudioConfig(BuiltinAudioClip.HOLD_MUSIC, volume=1)
        self.hold_sound_handle: PlayHandle | None = None

        # Ambient sound
        self.ambient_sound = ambient_sound
        self.ambient_sound_handle: PlayHandle | None = None

    async def set_session(self, session: AgentSession):
        """Sets the session and wires thinking sounds."""
        if self.session is not None:
            logger.warning("Session is already set")
            return

        # Set session
        self.session = session
        self.session.input.set_audio_enabled(not self.on_hold)

        # Wire thinking sounds to the already-running player
        self.player._agent_session = session
        session.on("agent_state_changed", self.player._agent_state_changed)

    async def start(self):
        """Starts the audio player."""
        if not self._player_started:
            await self.player.start(room=self.ctx.room)
            self._player_started = True

    # Hold controllers
    async def hold(self):
        """
        Holds the audio session by muting input, stopping ambient, and starting hold music.
        """
        if not self._player_started:
            await self.start()

        # Mute session input audio
        if self.session:
            self.session.input.set_audio_enabled(False)

        # Stop ambient sound
        if self.ambient_sound_handle:
            self.ambient_sound_handle.stop()
            await self.ambient_sound_handle.wait_for_playout()
            self.ambient_sound_handle = None

        # Stop existing hold music before playing new one
        if self.hold_sound_handle:
            self.hold_sound_handle.stop()
            await self.hold_sound_handle.wait_for_playout()
            self.hold_sound_handle = None

        # Start hold music
        self.hold_sound_handle = self.player.play(audio=self.hold_sound, loop=True)

        # Flag hold state
        self.on_hold = True

    async def unhold(self):
        """
        Unholds the audio session by unmuting input, starting ambient, and stopping hold music.
        """
        if not self._player_started:
            await self.start()

        # Unmute session input audio
        if self.session:
            self.session.input.set_audio_enabled(True)

        # Stop existing ambient before playing new one
        if self.ambient_sound_handle:
            self.ambient_sound_handle.stop()
            self.ambient_sound_handle = None

        # Start ambient music
        if self.ambient_sound:
            self.ambient_sound_handle = self.player.play(audio=self.ambient_sound, loop=True)

        # Stop hold music
        if self.hold_sound_handle:
            self.hold_sound_handle.stop()
            self.hold_sound_handle = None

        # Flag hold state
        self.on_hold = False

    # Close
    async def close(self):
        """
        Closes the audio controller and stops all audio.
        """
        # Close the player
        await self.player.aclose()
        # Reinitialize the player
        self.player = BackgroundAudioPlayer(
            thinking_sound=self.thinking_sound,
            stream_timeout_ms=STREAM_TIMEOUT_MS,
        )
        self._player_started = False

__all__ = ["AudioController"]
