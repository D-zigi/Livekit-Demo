"""
Utility functions for managing the lifecycle of job contexts in LiveKit.
"""
import logging
from livekit import api
from livekit.agents import JobContext

logger = logging.getLogger(__name__)

async def shutdown(ctx: JobContext, reason: str):
    """
    Shutdown the job context gracefully.

    Args:
        ctx: JobContext - The job context to shutdown.
        reason: str - The reason for shutdown.
    """
    ctx.shutdown(reason=reason)
    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=ctx.room.name,
        )
    )
    logger.info(f"Shutdown completed: {reason}")
