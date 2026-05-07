import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.camera import Camera
from app.models.recording import RecordingSession
from app.schemas.recording import RecordingSessionResponse, RecordingStatusResponse, RecordingFileInfo
from app.services import recorder
from app.config import settings

router = APIRouter(prefix="/api/recording", tags=["recording"])


def _source(camera: Camera) -> dict:
    if camera.camera_type in ("webcam", "usb_capture"):
        return {"type": camera.camera_type, "device_index": camera.device_index}
    return {"type": camera.camera_type, "rtsp_url": camera.rtsp_url}


@router.post("/{camera_id}/start")
async def start_recording(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    session_id = await recorder.start(camera_id, _source(camera), "manual", db)
    if session_id is None:
        raise HTTPException(400, "Already recording or failed to start")
    return {"status": "started", "session_id": session_id}


@router.post("/{camera_id}/stop")
async def stop_recording(camera_id: int, db: AsyncSession = Depends(get_db)):
    await recorder.stop(camera_id, db)
    return {"status": "stopped"}


@router.get("/{camera_id}/status", response_model=RecordingStatusResponse)
async def recording_status(camera_id: int, db: AsyncSession = Depends(get_db)):
    if not recorder.is_recording(camera_id):
        return RecordingStatusResponse(recording=False)
    info = recorder.recording_info(camera_id)
    result = await db.execute(
        select(RecordingSession).where(RecordingSession.id == info["session_id"])
    )
    session = result.scalar_one_or_none()
    if session:
        return RecordingStatusResponse(
            recording=True,
            recording_type=session.recording_type,
            started_at=session.start_time,
            file_path=session.file_path,
        )
    return RecordingStatusResponse(recording=True)


@router.get("/files", response_model=list[RecordingFileInfo])
async def list_recordings(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RecordingSession)
        .where(RecordingSession.status == "stopped")
        .order_by(desc(RecordingSession.start_time))
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    files = []
    rec_dir = settings.recordings_path()
    for s in sessions:
        if not s.file_path:
            continue
        fpath = rec_dir / s.file_path
        if not fpath.exists():
            continue
        files.append(RecordingFileInfo(
            filename=s.file_path,
            camera_id=s.camera_id,
            size_bytes=fpath.stat().st_size,
            created_at=s.start_time,
            recording_type=s.recording_type,
        ))
    return files


@router.get("/files/{filename}")
async def download_recording(filename: str):
    fpath = settings.recordings_path() / filename
    if not fpath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(fpath), media_type="video/mp4", filename=filename)


@router.delete("/files/{filename}", status_code=204)
async def delete_recording(filename: str, db: AsyncSession = Depends(get_db)):
    fpath = settings.recordings_path() / filename
    if fpath.exists():
        fpath.unlink()
    result = await db.execute(
        select(RecordingSession).where(RecordingSession.file_path == filename)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
