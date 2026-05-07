import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.routers import cameras, stream, recording, schedule, scanner
from app.services import stream_manager, motion_detector, recorder, scheduler as sched

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure output directories exist
    Path(settings.hls_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.recordings_dir).mkdir(parents=True, exist_ok=True)

    await init_db()

    # Wire up service dependencies
    motion_detector.configure(recorder, AsyncSessionLocal)
    sched.configure(recorder, stream_manager)

    # Start background services
    await stream_manager.start_watchdog()
    sched.start()

    # Auto-start continuous recording for enabled cameras
    from sqlalchemy import select
    from app.models.camera import Camera
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Camera).where(Camera.enabled.is_(True))
        )
        cameras_list = result.scalars().all()
        for cam in cameras_list:
            source = _build_source(cam)
            if source is None:
                continue
            if cam.continuous_recording:
                await recorder.start(cam.id, source, "continuous", db)
            if cam.motion_detection:
                motion_detector.start(cam.id, source, cam.motion_threshold)

    logger.info("CCTV streaming app started")
    yield

    # Shutdown
    stream_manager.stop_all()
    await stream_manager.stop_watchdog()
    motion_detector.stop_all()
    sched.stop()
    logger.info("CCTV streaming app stopped")


def _build_source(camera) -> dict | None:
    if camera.camera_type in ("webcam", "usb_capture"):
        if camera.device_index is None:
            return None
        return {"type": camera.camera_type, "device_index": camera.device_index}
    if camera.rtsp_url:
        return {"type": camera.camera_type, "rtsp_url": camera.rtsp_url}
    return None


app = FastAPI(title="CCTV Camera Streaming", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cameras.router)
app.include_router(stream.router)
app.include_router(recording.router)
app.include_router(schedule.router)
app.include_router(scanner.router)

# Serve HLS segments
Path(settings.hls_dir).mkdir(parents=True, exist_ok=True)
app.mount("/hls", StaticFiles(directory=settings.hls_dir), name="hls")


@app.get("/health")
async def health():
    return {"status": "ok"}
