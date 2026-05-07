import asyncio
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

_processes: dict[int, subprocess.Popen] = {}
_started_at: dict[int, datetime] = {}
_camera_sources: dict[int, dict] = {}  # camera_id -> {type, rtsp_url/device_index}
_watchdog_task: asyncio.Task | None = None


def _build_hls_cmd(camera_id: int, source: dict) -> list[str]:
    hls_path = settings.hls_path(camera_id)
    hls_path.mkdir(parents=True, exist_ok=True)
    playlist = str(hls_path / "stream.m3u8")

    hls_flags = f"hls_time={settings.hls_segment_time}:hls_list_size={settings.hls_list_size}:hls_flags=delete_segments"

    if source["type"] in ("webcam", "usb_capture"):
        return [
            "ffmpeg", "-y",
            "-f", "v4l2",
            "-i", f"/dev/video{source['device_index']}",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-c:a", "aac",
            "-f", "hls",
            f"-hls_time={settings.hls_segment_time}",
            f"-hls_list_size={settings.hls_list_size}",
            "-hls_flags", "delete_segments",
            playlist,
        ]
    else:
        return [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", source["rtsp_url"],
            "-c:v", "copy", "-c:a", "aac",
            "-f", "hls",
            f"-hls_time={settings.hls_segment_time}",
            f"-hls_list_size={settings.hls_list_size}",
            "-hls_flags", "delete_segments",
            playlist,
        ]


def start(camera_id: int, source: dict) -> bool:
    if camera_id in _processes and _processes[camera_id].poll() is None:
        return True  # already running
    _camera_sources[camera_id] = source
    cmd = _build_hls_cmd(camera_id, source)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _processes[camera_id] = proc
        _started_at[camera_id] = datetime.utcnow()
        logger.info("Started HLS stream for camera %d (pid=%d)", camera_id, proc.pid)
        return True
    except Exception as exc:
        logger.error("Failed to start stream for camera %d: %s", camera_id, exc)
        return False


def stop(camera_id: int):
    proc = _processes.pop(camera_id, None)
    _started_at.pop(camera_id, None)
    _camera_sources.pop(camera_id, None)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    hls_path = settings.hls_path(camera_id)
    for f in hls_path.glob("*"):
        f.unlink(missing_ok=True)
    logger.info("Stopped HLS stream for camera %d", camera_id)


def status(camera_id: int) -> dict:
    proc = _processes.get(camera_id)
    if proc is None or proc.poll() is not None:
        return {"active": False, "started_at": None, "segment_count": 0}
    hls_path = settings.hls_path(camera_id)
    segments = list(hls_path.glob("*.ts"))
    return {
        "active": True,
        "started_at": _started_at.get(camera_id),
        "segment_count": len(segments),
    }


def all_active() -> list[int]:
    return [cid for cid, p in _processes.items() if p.poll() is None]


async def _watchdog():
    while True:
        await asyncio.sleep(10)
        for camera_id, source in list(_camera_sources.items()):
            proc = _processes.get(camera_id)
            if proc is None or proc.poll() is not None:
                logger.warning("Stream for camera %d died, restarting…", camera_id)
                start(camera_id, source)


async def start_watchdog():
    global _watchdog_task
    _watchdog_task = asyncio.create_task(_watchdog())


async def stop_watchdog():
    if _watchdog_task:
        _watchdog_task.cancel()
        try:
            await _watchdog_task
        except asyncio.CancelledError:
            pass


def stop_all():
    for camera_id in list(_processes.keys()):
        stop(camera_id)
