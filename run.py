"""
Run the LiveKit worker.
"""
from livekit.agents import cli, WorkerOptions
from app.main import entrypoint
from shared.core.config import settings

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            ws_url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            agent_name=settings.AGENT_NAME,
            port=settings.PORT,
            entrypoint_fnc=entrypoint,
        )
    )
