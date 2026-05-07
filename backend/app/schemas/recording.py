from datetime import datetime
from pydantic import BaseModel


class RecordingSessionResponse(BaseModel):
    id: int
    camera_id: int
    start_time: datetime
    end_time: datetime | None
    file_path: str | None
    file_size: int | None
    recording_type: str
    status: str

    model_config = {"from_attributes": True}


class RecordingStatusResponse(BaseModel):
    recording: bool
    recording_type: str | None = None
    started_at: datetime | None = None
    file_path: str | None = None


class RecordingFileInfo(BaseModel):
    filename: str
    camera_id: int | None
    size_bytes: int
    created_at: datetime
    recording_type: str | None
