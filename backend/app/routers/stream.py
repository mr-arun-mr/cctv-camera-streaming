from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.camera import Camera
from app.services import stream_manager

router = APIRouter(prefix="/api/stream", tags=["stream"])


def _source(camera: Camera) -> dict:
    if camera.camera_type in ("webcam", "usb_capture"):
        return {"type": camera.camera_type, "device_index": camera.device_index}
    return {"type": camera.camera_type, "rtsp_url": camera.rtsp_url}


@router.post("/{camera_id}/start")
async def start_stream(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    if not camera.enabled:
        raise HTTPException(400, "Camera is disabled")
    ok = stream_manager.start(camera_id, _source(camera))
    if not ok:
        raise HTTPException(500, "Failed to start stream")
    return {"status": "started"}


@router.post("/{camera_id}/stop")
async def stop_stream(camera_id: int):
    stream_manager.stop(camera_id)
    return {"status": "stopped"}


@router.get("/{camera_id}/status")
async def stream_status(camera_id: int):
    return stream_manager.status(camera_id)


@router.get("/active")
async def active_streams():
    return {"camera_ids": stream_manager.all_active()}
