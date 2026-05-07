import json
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.schedule import RecordingSchedule
from app.models.camera import Camera

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()
_recorder = None
_stream_manager = None


def configure(recorder_module, stream_manager_module):
    global _recorder, _stream_manager
    _recorder = recorder_module
    _stream_manager = stream_manager_module


async def _check_schedules():
    now = datetime.now()
    current_day = now.weekday()  # 0=Monday
    current_time = now.strftime("%H:%M")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RecordingSchedule, Camera)
            .join(Camera, RecordingSchedule.camera_id == Camera.id)
            .where(RecordingSchedule.enabled.is_(True))
            .where(Camera.enabled.is_(True))
        )
        rows = result.all()

    for schedule, camera in rows:
        try:
            days = json.loads(schedule.days_of_week)
        except Exception:
            continue

        in_day = current_day in days
        in_time = schedule.start_time <= current_time < schedule.end_time

        source = _build_source(camera)
        if source is None:
            continue

        async with AsyncSessionLocal() as db:
            if in_day and in_time:
                if _recorder and not _recorder.is_recording(camera.id):
                    await _recorder.start(camera.id, source, "scheduled", db)
            else:
                if _recorder and _recorder.is_recording(camera.id):
                    info = _recorder.recording_info(camera.id)
                    if info and _is_scheduled_recording(camera.id):
                        await _recorder.stop(camera.id, db)


def _build_source(camera: Camera) -> dict | None:
    if camera.camera_type in ("webcam", "usb_capture"):
        if camera.device_index is None:
            return None
        return {"type": camera.camera_type, "device_index": camera.device_index}
    if camera.rtsp_url:
        return {"type": camera.camera_type, "rtsp_url": camera.rtsp_url}
    return None


def _is_scheduled_recording(camera_id: int) -> bool:
    info = _recorder.recording_info(camera_id) if _recorder else None
    return info is not None


def start():
    _scheduler.add_job(_check_schedules, "interval", minutes=1, id="schedule_checker")
    _scheduler.start()
    logger.info("Scheduler started")


def stop():
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
