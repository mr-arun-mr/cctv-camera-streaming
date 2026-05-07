import threading
import logging
import time
import cv2
from app.config import settings

logger = logging.getLogger(__name__)

_threads: dict[int, threading.Thread] = {}
_stop_flags: dict[int, threading.Event] = {}

# Injected at startup to avoid circular import
_recorder = None
_db_factory = None


def configure(recorder_module, db_factory):
    global _recorder, _db_factory
    _recorder = recorder_module
    _db_factory = db_factory


def _worker(camera_id: int, source: dict, threshold: int, stop_event: threading.Event):
    if source["type"] in ("webcam", "usb_capture"):
        cap = cv2.VideoCapture(source["device_index"])
    else:
        cap = cv2.VideoCapture(source["rtsp_url"])

    if not cap.isOpened():
        logger.error("Motion detector: cannot open source for camera %d", camera_id)
        return

    prev_gray = None
    motion_end_time = 0.0
    cooldown = settings.motion_cooldown_seconds

    import asyncio

    loop = asyncio.new_event_loop()

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                cap.release()
                if source["type"] in ("webcam", "usb_capture"):
                    cap = cv2.VideoCapture(source["device_index"])
                else:
                    cap = cv2.VideoCapture(source["rtsp_url"])
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                continue

            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            motion_area = sum(cv2.contourArea(c) for c in contours)

            now = time.time()
            if motion_area > threshold:
                motion_end_time = now + cooldown
                if _recorder and not _recorder.is_recording(camera_id) and _db_factory:
                    async def _start_rec():
                        async with _db_factory() as db:
                            await _recorder.start(camera_id, source, "motion", db)
                    loop.run_until_complete(_start_rec())
            elif now > motion_end_time and _recorder and _recorder.is_recording(camera_id) and _db_factory:
                async def _stop_rec():
                    async with _db_factory() as db:
                        await _recorder.stop(camera_id, db)
                loop.run_until_complete(_stop_rec())

            prev_gray = gray
            time.sleep(0.1)
    finally:
        cap.release()
        loop.close()
        logger.info("Motion detector stopped for camera %d", camera_id)


def start(camera_id: int, source: dict, threshold: int):
    if camera_id in _threads and _threads[camera_id].is_alive():
        return
    stop_event = threading.Event()
    _stop_flags[camera_id] = stop_event
    t = threading.Thread(
        target=_worker,
        args=(camera_id, source, threshold, stop_event),
        daemon=True,
        name=f"motion-{camera_id}",
    )
    _threads[camera_id] = t
    t.start()
    logger.info("Motion detector started for camera %d", camera_id)


def stop(camera_id: int):
    flag = _stop_flags.pop(camera_id, None)
    if flag:
        flag.set()
    _threads.pop(camera_id, None)


def stop_all():
    for camera_id in list(_stop_flags.keys()):
        stop(camera_id)
