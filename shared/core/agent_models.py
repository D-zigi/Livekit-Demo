"""
Agent Models
"""
from google.genai.types import (
    AutomaticActivityDetection,
    Behavior,
    FunctionResponseScheduling,
    Modality,
    RealtimeInputConfig,
    StartSensitivity,
    ThinkingConfig,
)
from livekit.plugins import google, openai, elevenlabs, inworld, soniox
from livekit.agents import NOT_GIVEN, inference

from shared.core.config import settings
from shared.models.agent import Agent, AgentRead, LanguageMap

from shared.core.agent_config import AGENT

# Google
def google_realtime_model(agent: Agent | AgentRead = AGENT, voice: bool = True) -> google.realtime.RealtimeModel:
    """Returns a Google realtime model for the given agent."""
    return google.realtime.RealtimeModel(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=NOT_GIVEN,
        api_key=settings.GEMINI_API_KEY,
        model="gemini-live-2.5-flash-native-audio",
        voice="Kore" if agent.gender == "female" else "Charon",
        modalities=[Modality.AUDIO] if voice else [Modality.TEXT, Modality.AUDIO],
        language=(
            # NOTE: Hebrew is not supported by Google Realtime API yet
            agent.language
            if agent.language != "he-IL"
            else NOT_GIVEN
        ),
        temperature=agent.temperature,
        # thinking_config=ThinkingConfig(
        #     include_thoughts=True,
        #     thinking_budget=2048,
        #     # thinking_level=ThinkingLevel.LOW,
        # ),
        # tool_behavior=Behavior.NON_BLOCKING,
        # tool_response_scheduling=FunctionResponseScheduling.WHEN_IDLE,
        # proactivity=True,
        # enable_affective_dialog=True,
    )

def google_llm_model(agent: Agent | AgentRead = AGENT) -> google.LLM:
    """Returns a Google LLM model for the given agent."""
    return google.LLM(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location="global",
        # api_key=settings.GEMINI_API_KEY,
        model="gemini-3-flash-preview",
        temperature=agent.temperature,
    )

def google_tts_model(agent: Agent | AgentRead = AGENT) -> google.beta.GeminiTTS:
    """Returns a Google TTS model for the given agent."""
    return google.beta.GeminiTTS(
        model="gemini-2.5-flash-preview-tts",
        voice_name=agent.voice_model,
        instructions=agent.voice_style or NOT_GIVEN,
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location="us-central1",
    )

# OpenAI
def openai_realtime_model(agent: Agent | AgentRead = AGENT, voice: bool = True) -> openai.realtime.RealtimeModel:
    """Returns an OpenAI realtime model for the given agent."""
    return openai.realtime.RealtimeModel(
        model="gpt-4o-realtime-preview",
        # voice=agent.voice_model,
        modalities=["text"] if not voice else ["text", "audio"],
        api_key=settings.OPENAI_API_KEY,
        temperature=agent.temperature,
    )

def openai_llm_model(agent: Agent | AgentRead = AGENT) -> openai.LLM:
    """Returns an OpenAI LLM model for the given agent."""
    return openai.LLM(
        model="gpt-4.1",
        api_key=settings.OPENAI_API_KEY,
        temperature=agent.temperature,
    )

def openai_tts_model(agent: Agent | AgentRead = AGENT) -> openai.TTS:
    """Returns an OpenAI TTS model for the given agent."""
    return openai.TTS(
        model="gpt-4o-mini-tts",
        voice="alloy",
        speed=1.35,
        api_key=settings.OPENAI_API_KEY,
        instructions=agent.voice_style or NOT_GIVEN,
    )

# InworldAI
def inworldai_tts_model(agent: Agent | AgentRead = AGENT):
    """Returns an InworldAI TTS model for the given agent."""
    return inworld.TTS(
        api_key=settings.INWORLDAI_API_KEY,
        model="inworld-tts-2",
        voice="Yael" if agent.gender == "female" else "Oren",
        speaking_rate=1.1,
    )

# ElevenLabs
def elevenlabs_tts_model(agent: Agent | AgentRead = AGENT):
    """Returns an ElevenLabs TTS model for the given agent."""
    return inference.TTS(
        model="elevenlabs/eleven_multilingual_v2",
        voice="Xb7hH8MSUJpSbSDYk0k2", 
        language="he"
    )
    return elevenlabs.TTS(
        api_key=settings.ELEVENLABS_API_KEY,
        model="eleven_v3",
        voice_id="Xb7hH8MSUJpSbSDYk0k2", 
        language="en"
    )

# Soniox
def soniox_stt_model(agent: Agent | AgentRead = AGENT):
    """Returns a Soniox STT model for the given agent."""
    return soniox.STT(
        api_key=settings.SONIOX_API_KEY,
        params=soniox.STTOptions(
            model = "stt-rt-v4",
            language_hints=list(set([lang[:2] for lang in LanguageMap.keys()])),
            enable_language_identification=True
        )
    )

def soniox_tts_model(agent: Agent | AgentRead = AGENT):
    """Returns a Soniox TTS model for the given agent."""
    return soniox.TTS(
        api_key=settings.SONIOX_API_KEY,
        model="tts-rt-v1-preview",
        language=agent.language[:2],
        voice="Maya",
    )


__all__ = [
    "google_realtime_model",
    "google_tts_model",
    "openai_realtime_model",
    "inworldai_tts_model",
    "elevenlabs_tts_model",
    "soniox_stt_model"
]
