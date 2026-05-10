"""
Config module
"""
from typing import Literal
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """auto load config from .env and validate settings"""
    # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support

    # Config
    PORT: int = 8076

    # Livekit
    AGENT_NAME: str
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # MCPs
    MAIN_MCP_URL: str
    MAIN_MCP_KEY: str

    # Google
    GEMINI_API_KEY: str
    GOOGLE_CLOUD_PROJECT: str
    # GOOGLE_CLOUD_LOCATION: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    GCP_BUCKET_NAME: str

    # OpenAI
    OPENAI_API_KEY: str

    # ElevenLabs
    ELEVENLABS_API_KEY: str

    # AssemblyAI
    ASSEMBLYAI_API_KEY: str

    # InworldAI
    INWORLDAI_API_KEY: str

    # Soniox
    SONIOX_API_KEY: str

    # Groq
    GROQ_API_KEY: str

    # Project - Secrets
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Project - Info
    PROJECT_NAME: str = "Hyper-Sales - Livekit"
    PROJECT_DESCRIPTION: str = "Livekit for Hyper-Sales"
    PROJECT_VERSION: str = "0.1.0"
    PUBLIC_VERSION: str = "v1"

    # Demo Configuration
    BACKGROUND_NOISE: bool = True

    class Config:
        """config for pydantic settings"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

settings = Settings() # type: ignore[call-arg]
