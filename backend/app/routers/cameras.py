import time
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse, ConnectionTestResult

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


def _camera_source(camera: Camera) -> dict:
    if camera.camera_type in ("webcam", "usb_capture"):
        return {"type": camera.camera_type, "device_index": camera.device_index}
    return {"type": camera.camera_type, "rtsp_url": camera.rtsp_url}


@router.get("/", response_model=list[CameraResponse])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.id))
    return result.scalars().all()


@router.post("/", response_model=CameraResponse, status_code=201)
async def create_camera(body: CameraCreate, db: AsyncSession = Depends(get_db)):
    camera = Camera(**body.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    return camera


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: int, body: CameraUpdate, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(camera, field, value)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    from app.services import stream_manager, motion_detector
    stream_manager.stop(camera_id)
    motion_detector.stop(camera_id)
    await db.delete(camera)
    await db.commit()


@router.post("/{camera_id}/test", response_model=ConnectionTestResult)
async def test_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")

    if camera.camera_type in ("webcam", "usb_capture"):
        try:
            import cv2
            t0 = time.time()
            cap = cv2.VideoCapture(camera.device_index)
            ok = cap.isOpened()
            cap.release()
            latency = int((time.time() - t0) * 1000)
            return ConnectionTestResult(ok=ok, latency_ms=latency if ok else None)
        except Exception as exc:
            return ConnectionTestResult(ok=False, error=str(exc))

    if not camera.rtsp_url:
        return ConnectionTestResult(ok=False, error="No RTSP URL configured")
    try:
        t0 = time.time()
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-rtsp_transport", "tcp",
             "-i", camera.rtsp_url, "-show_entries", "stream=codec_type",
             "-of", "csv=p=0"],
            capture_output=True, timeout=8,
        )
        latency = int((time.time() - t0) * 1000)
        if result.returncode == 0:
            return ConnectionTestResult(ok=True, latency_ms=latency)
        return ConnectionTestResult(ok=False, error=result.stderr.decode()[:200])
    except subprocess.TimeoutExpired:
        return ConnectionTestResult(ok=False, error="Connection timed out")
    except Exception as exc:
        return ConnectionTestResult(ok=False, error=str(exc))
