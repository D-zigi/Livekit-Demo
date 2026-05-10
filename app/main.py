import logging
from typing import cast

from livekit.plugins import silero
from livekit.agents import AudioConfig, AutoSubscribe, BackgroundAudioPlayer, BuiltinAudioClip, JobContext, AgentSession

from app.core import agent_models
from app.core.agent_config import AGENT

from app.services.agent import CallAgent
from app.services.copilot_agent import CopilotAgent

from app.utils.mcp import get_integrations_mcp_toolset


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def entrypoint(ctx: JobContext):
    # Realtime Agent Session
    session = AgentSession(
        llm=agent_models.google_realtime_model(),
        preemptive_generation=True,
        allow_interruptions=True,
        user_away_timeout=10,
    )

    # Main agent setup
    agent = CallAgent(
        agent=AGENT,
    )

    # MCP servers initialization
    integrations_mcp_toolset = get_integrations_mcp_toolset(business_id=cast(str, AGENT.business_id))

    # Copilot agent setup
    copilot_agent = CopilotAgent(
        main_agent=agent,
        main_session=session,
        tools=[integrations_mcp_toolset],
    )

    # Copilot session
    copilot_session = AgentSession(
        stt=agent_models.soniox_stt_model(),
        llm=agent_models.google_llm_model(),
        vad=silero.VAD.load(),
        tts=agent_models.soniox_tts_model(),
        allow_interruptions=True,
        user_away_timeout=10,
    )
    copilot_session.output.set_audio_enabled(False)

    # Initialize background audio
    background_audio = BackgroundAudioPlayer(
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )

    # connect to the room
    logger.info("Connecting to room %s", ctx.room.name)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for a participant to join
    await ctx.wait_for_participant()
    logger.info("Participant joined")

    # Start sessions
    await background_audio.start(room=ctx.room, agent_session=copilot_session)
    await session.start(
        room=ctx.room,
        agent=agent,
    )
    await copilot_session.start(
        room=ctx.room,
        agent=copilot_agent,
    )
