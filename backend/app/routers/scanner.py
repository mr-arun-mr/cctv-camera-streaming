import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.camera import Camera
from app.services import network_scanner, onvif_scanner, local_webcam_scanner, dvr_prober

router = APIRouter(prefix="/api/scan", tags=["scanner"])


class DVRProbeRequest(BaseModel):
    ip: str
    username: str = "admin"
    password: str = "admin"
    brand: str = "generic"
    channel_count: int = 16


class DVRAddAllRequest(BaseModel):
    channels: list[dict]
    dvr_host: str
    brand: str
    username: str = ""
    password: str = ""


class ProbeRequest(BaseModel):
    ip: str
    port: int = 554
    username: str = ""
    password: str = ""


@router.post("/network")
async def start_network_scan():
    job_id = str(uuid.uuid4())
    network_scanner.start_scan(job_id)
    return {"job_id": job_id}


@router.get("/network/{job_id}")
async def get_network_scan(job_id: str):
    result = network_scanner.get_scan(job_id)
    if result is None:
        raise HTTPException(404, "Scan job not found")
    return result


@router.post("/onvif")
async def onvif_scan():
    return await onvif_scanner.discover()


@router.get("/webcams")
async def scan_webcams():
    return await local_webcam_scanner.scan()


@router.post("/dvr")
async def probe_dvr(body: DVRProbeRequest):
    channels = await dvr_prober.probe_dvr(
        body.ip, body.username, body.password, body.brand, body.channel_count
    )
    return {"ip": body.ip, "brand": body.brand, "channels": channels}


@router.post("/dvr/add-all", status_code=201)
async def add_all_dvr_channels(body: DVRAddAllRequest, db: AsyncSession = Depends(get_db)):
    created = []
    for ch in body.channels:
        camera = Camera(
            name=ch.get("name", f"Channel {ch['channel']}"),
            ip_address=body.dvr_host,
            rtsp_url=ch["rtsp_url"],
            username=body.username,
            password=body.password,
            camera_type="dvr_channel",
            dvr_host=body.dvr_host,
            channel_number=ch["channel"],
            dvr_brand=body.brand,
        )
        db.add(camera)
        created.append(camera)
    await db.commit()
    return {"created": len(created)}


@router.post("/probe")
async def probe_ip(body: ProbeRequest):
    import subprocess
    urls_to_try = [
        f"rtsp://{body.username}:{body.password}@{body.ip}:{body.port}/",
        f"rtsp://{body.ip}:{body.port}/",
        f"rtsp://{body.ip}:{body.port}/stream",
        f"rtsp://{body.ip}:{body.port}/live",
    ] if body.username else [
        f"rtsp://{body.ip}:{body.port}/",
        f"rtsp://{body.ip}:{body.port}/stream",
        f"rtsp://{body.ip}:{body.port}/live",
    ]
    for url in urls_to_try:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-rtsp_transport", "tcp",
                 "-i", url, "-show_entries", "stream=codec_type", "-of", "csv=p=0"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return {"rtsp_url": url, "reachable": True}
        except Exception:
            continue
    return {"rtsp_url": None, "reachable": False}
