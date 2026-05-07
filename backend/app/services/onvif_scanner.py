import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def _discover_sync() -> list[dict]:
    results = []
    try:
        from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
        wsd = WSDiscovery()
        wsd.start()
        services = wsd.searchServices(timeout=5)
        wsd.stop()

        for svc in services:
            scopes = [str(s) for s in svc.getScopes()]
            if not any("onvif" in s.lower() for s in scopes):
                continue
            xaddrs = [str(x) for x in svc.getXAddrs()]
            ip = ""
            for x in xaddrs:
                if x.startswith("http"):
                    parts = x.replace("http://", "").replace("https://", "").split("/")
                    ip = parts[0].split(":")[0]
                    break
            manufacturer = ""
            model = ""
            for s in scopes:
                if "onvif://www.onvif.org/hardware/" in s:
                    model = s.split("/")[-1]
                if "onvif://www.onvif.org/name/" in s:
                    manufacturer = s.split("/")[-1]
            results.append({
                "ip": ip,
                "xaddr": xaddrs[0] if xaddrs else "",
                "manufacturer": manufacturer,
                "model": model,
                "rtsp_url": "",
            })
    except Exception as exc:
        logger.error("ONVIF discovery error: %s", exc)
    return results


async def discover() -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _discover_sync)


async def get_rtsp_url(ip: str, port: int, username: str, password: str) -> str | None:
    try:
        from onvif import ONVIFCamera
        import zeep

        def _fetch():
            cam = ONVIFCamera(ip, port, username, password)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            if not profiles:
                return None
            token = profiles[0].token
            req = media.create_type("GetStreamUri")
            req.ProfileToken = token
            req.StreamSetup = {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"},
            }
            uri = media.GetStreamUri(req)
            return uri.Uri

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _fetch)
    except Exception as exc:
        logger.warning("Could not fetch RTSP URL from %s:%d: %s", ip, port, exc)
        return None
