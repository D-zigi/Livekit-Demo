"""
User state controller service
"""
import asyncio
import logging
from typing import Optional
from livekit.agents import AgentSession, UserStateChangedEvent
from livekit.agents.voice import SpeechHandle
from livekit.agents.voice.events import UserState

logger = logging.getLogger(__name__)

class UserStateController():
    def __init__(
        self,
        session: AgentSession,
        user_away_pings: int = 2,
        user_away_ping_delay: Optional[float] = None
    ):
        """
        Initialize an UserStateController instance.

        Args:
            session (AgentSession): The agent session to control audio input.
            user_away_pings (int): Number of ping attempts before closing the session.
            user_away_ping_delay (float): Delay in seconds between ping attempts. Defaults to Session user_away_timeout or 10s.
        """
        # Controllables
        self.session = session

        # State props
        self.user_state: Optional[UserState] = None

        # Away State props
        self.user_away_task_ref: asyncio.Task | None = None
        self.user_away_pings = user_away_pings
        self.user_away_ping_delay = (
            user_away_ping_delay
            or self.session._opts.user_away_timeout
            or 10
        )

    def handle_user_state_changed(self, event: UserStateChangedEvent):
        """
        Handle user state changes to manage presence detection tasks.

        args:
            event: UserStateChangedEvent - The event containing the new user state.
        """
        self.user_state = event.new_state
        # If the user goes away, start the presence task
        if (
            event.new_state == "away"
            and (
                not self.user_away_task_ref
                or self.user_away_task_ref.done()
            )
        ):
            self.user_away_task_ref = asyncio.create_task(self._user_away_task())
        # If the user starts speaking, cancel the user away task
        elif (
            event.new_state == "speaking"
            and self.user_away_task_ref is not None
        ):
            self.user_away_task_ref.cancel()
            self.user_away_task_ref = None

    async def _user_away_task(self):
        """
        Check if the user is still present in the call.
        If the user does not respond after multiple attempts, close the session.
        """
        speech_handles: list[SpeechHandle] = []
        try:
            # Try to ping the user `self.user_away_pings` times, if we get no answer, close the session
            for attempt in range(self.user_away_pings):
                logger.debug(f"Ping attempt {attempt + 1}: checking if user is still present...")
                handle = await self.session.generate_reply(
                    instructions=(
                        "The user has been inactive. Politely check if the user is still present. Don't end the call yet."
                        if attempt == 0
                        else "The user has not responded to previous checks. Please ask if they are still there."
                    ),
                    allow_interruptions=True
                )
                speech_handles.append(handle)
                await asyncio.sleep(self.user_away_ping_delay)

            logger.debug("User not responding after multiple attempts, closing session...")
            self.session.shutdown(drain=True)
        except asyncio.CancelledError:
            # Task was canceled because user returned
            for handle in speech_handles:
                handle.interrupt(force=True)
            logger.debug("User returned, cancelling inactivity check")
            return
        except Exception as e:
            logger.error(f"Error in user presence task: {str(e)}")
            # Close the session on error
            self.session.shutdown(drain=True)

    def close(self):
        """Cleanup any pending tasks."""
        if self.user_away_task_ref:
            self.user_away_task_ref.cancel()
            self.user_away_task_ref = None

__all__ = [
    "UserStateController"
]
