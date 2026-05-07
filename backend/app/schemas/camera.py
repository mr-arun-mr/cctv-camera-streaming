from datetime import datetime
from pydantic import BaseModel


class CameraBase(BaseModel):
    name: str
    ip_address: str | None = None
    rtsp_url: str | None = None
    device_index: int | None = None
    device_path: str | None = None
    username: str | None = None
    password: str | None = None
    camera_type: str = "ip"
    dvr_host: str | None = None
    channel_number: int | None = None
    dvr_brand: str | None = None
    enabled: bool = True
    motion_detection: bool = False
    motion_threshold: int = 500
    continuous_recording: bool = False


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    rtsp_url: str | None = None
    device_index: int | None = None
    device_path: str | None = None
    username: str | None = None
    password: str | None = None
    camera_type: str | None = None
    dvr_host: str | None = None
    channel_number: int | None = None
    dvr_brand: str | None = None
    enabled: bool | None = None
    motion_detection: bool | None = None
    motion_threshold: int | None = None
    continuous_recording: bool | None = None


class CameraResponse(CameraBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None
