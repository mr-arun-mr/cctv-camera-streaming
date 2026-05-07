import asyncio
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)

RTSP_URL_PATTERNS = {
    "hikvision": "rtsp://{user}:{pwd}@{ip}:554/Streaming/Channels/{ch:02d}01",
    "dahua": "rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel={ch}&subtype=0",
    "uniview": "rtsp://{user}:{pwd}@{ip}:554/unicast/c{ch}/s0/live",
    "generic": [
        "rtsp://{user}:{pwd}@{ip}:554/ch{ch:02d}",
        "rtsp://{user}:{pwd}@{ip}:554/channel{ch}",
        "rtsp://{user}:{pwd}@{ip}:554/h264/ch{ch}/main/av_stream",
        "rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel={ch}&subtype=0",
    ],
}


def _build_urls(ip: str, username: str, password: str, brand: str, channel: int) -> list[str]:
    fmt_args = {"user": username, "pwd": password, "ip": ip, "ch": channel}
    pattern = RTSP_URL_PATTERNS.get(brand, RTSP_URL_PATTERNS["generic"])
    if isinstance(pattern, list):
        return [p.format(**fmt_args) for p in pattern]
    return [pattern.format(**fmt_args)]


def _probe_url(url: str) -> bool:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-rtsp_transport", "tcp",
                "-i", url,
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
            ],
            capture_output=True,
            timeout=6,
        )
        return result.returncode == 0
    except Exception:
        return False


async def _probe_channel(ip: str, username: str, password: str, brand: str, channel: int) -> dict | None:
    urls = _build_urls(ip, username, password, brand, channel)
    loop = asyncio.get_event_loop()
    for url in urls:
        ok = await loop.run_in_executor(_executor, _probe_url, url)
        if ok:
            return {
                "channel": channel,
                "rtsp_url": url,
                "name": f"Channel {channel}",
            }
    return None


async def probe_dvr(
    ip: str,
    username: str,
    password: str,
    brand: str = "generic",
    channel_count: int = 16,
) -> list[dict]:
    tasks = [
        _probe_channel(ip, username, password, brand, ch)
        for ch in range(1, channel_count + 1)
    ]
    results = await asyncio.gather(*tasks)
    found = [r for r in results if r is not None]
    logger.info("DVR probe %s: found %d/%d channels", ip, len(found), channel_count)
    return found
