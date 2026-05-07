from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:////app/cctv.db"
    hls_dir: str = "/app/hls"
    recordings_dir: str = "/app/recordings"
    hls_segment_time: int = 2
    hls_list_size: int = 5
    motion_cooldown_seconds: int = 30
    scan_timeout_seconds: int = 30

    model_config = {"env_file": ".env"}

    def hls_path(self, camera_id: int) -> Path:
        return Path(self.hls_dir) / str(camera_id)

    def recordings_path(self) -> Path:
        return Path(self.recordings_dir)


settings = Settings()
