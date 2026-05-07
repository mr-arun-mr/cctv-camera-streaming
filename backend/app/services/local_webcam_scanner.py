import asyncio
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)


def _probe_devices_sync() -> list[dict]:
    import cv2
    devices = []
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            continue
        ret, _ = cap.read()
        if not ret:
            cap.release()
            continue
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        device_path = f"/dev/video{index}"
        is_capture_card = _check_capture_card(device_path)
        name = _get_device_name(device_path) or f"Camera {index}"
        devices.append({
            "device_index": index,
            "device_path": device_path,
            "width": width,
            "height": height,
            "name": name,
            "is_capture_card": is_capture_card,
        })
    return devices


def _check_capture_card(device_path: str) -> bool:
    if not Path(device_path).exists():
        return False
    try:
        result = subprocess.run(
            ["v4l2-ctl", f"--device={device_path}", "--list-inputs"],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout.lower()
        return any(kw in output for kw in ("composite", "s-video", "svideo", "component", "hdmi"))
    except Exception:
        return False


def _get_device_name(device_path: str) -> str | None:
    if not Path(device_path).exists():
        return None
    try:
        result = subprocess.run(
            ["v4l2-ctl", f"--device={device_path}", "--info"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "Card type" in line:
                return line.split(":", 1)[-1].strip()
    except Exception:
        pass
    return None


async def scan() -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _probe_devices_sync)
