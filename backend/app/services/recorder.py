import subprocess
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.config import settings
from app.models.recording import RecordingSession

logger = logging.getLogger(__name__)

_processes: dict[int, tuple[subprocess.Popen, int]] = {}  # camera_id -> (proc, session_id)


def _build_record_cmd(camera_id: int, source: dict, out_path: str) -> list[str]:
    if source["type"] in ("webcam", "usb_capture"):
        return [
            "ffmpeg", "-y",
            "-f", "v4l2",
            "-i", f"/dev/video{source['device_index']}",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            out_path,
        ]
    else:
        return [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", source["rtsp_url"],
            "-c", "copy",
            out_path,
        ]


async def start(camera_id: int, source: dict, recording_type: str, db: AsyncSession) -> int | None:
    if camera_id in _processes and _processes[camera_id][0].poll() is None:
        return None  # already recording

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{camera_id}_{recording_type}_{ts}.mp4"
    out_path = str(settings.recordings_path() / filename)
    Path(settings.recordings_dir).mkdir(parents=True, exist_ok=True)

    session = RecordingSession(
        camera_id=camera_id,
        file_path=filename,
        recording_type=recording_type,
        status="recording",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    cmd = _build_record_cmd(camera_id, source, out_path)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _processes[camera_id] = (proc, session.id)
        logger.info("Started %s recording for camera %d -> %s", recording_type, camera_id, filename)
        return session.id
    except Exception as exc:
        logger.error("Failed to start recording for camera %d: %s", camera_id, exc)
        await db.execute(
            update(RecordingSession).where(RecordingSession.id == session.id).values(status="error")
        )
        await db.commit()
        return None


async def stop(camera_id: int, db: AsyncSession):
    entry = _processes.pop(camera_id, None)
    if entry is None:
        return
    proc, session_id = entry
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    result = await db.execute(select(RecordingSession).where(RecordingSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.end_time = datetime.utcnow()
        session.status = "stopped"
        file_path = settings.recordings_path() / session.file_path
        if file_path.exists():
            session.file_size = file_path.stat().st_size
        await db.commit()
    logger.info("Stopped recording for camera %d", camera_id)


def is_recording(camera_id: int) -> bool:
    entry = _processes.get(camera_id)
    return entry is not None and entry[0].poll() is None


def recording_info(camera_id: int) -> dict | None:
    entry = _processes.get(camera_id)
    if entry is None or entry[0].poll() is not None:
        return None
    return {"session_id": entry[1]}


async def stop_all(db: AsyncSession):
    for camera_id in list(_processes.keys()):
        await stop(camera_id, db)
