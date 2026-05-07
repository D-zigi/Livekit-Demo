"""
Egress Utils
"""
from livekit import api
from livekit.agents import JobContext
from shared.core.config import settings

async def start_recording(ctx: JobContext):
    """Start recording the conversation."""
    req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[
            api.EncodedFileOutput(
                file_type=api.EncodedFileType.OGG,
                filepath=f"livekit/{ctx.room.name}.ogg",
                gcp=api.GCPUpload(
                    credentials=open(settings.GOOGLE_APPLICATION_CREDENTIALS).read(),
                    bucket=settings.GCP_BUCKET_NAME,
                ),
            )
        ],
    )

    lkapi = api.LiveKitAPI()
    egress_info = await lkapi.egress.start_room_composite_egress(req)
    await lkapi.aclose()
    return egress_info
