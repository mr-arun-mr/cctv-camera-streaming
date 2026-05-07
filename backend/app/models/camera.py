from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    rtsp_url: Mapped[str | None] = mapped_column(String, nullable=True)
    device_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_path: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)
    # onvif | ip | rtsp | webcam | usb_capture | dvr_channel
    camera_type: Mapped[str] = mapped_column(String, default="ip")
    dvr_host: Mapped[str | None] = mapped_column(String, nullable=True)
    channel_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dvr_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    motion_detection: Mapped[bool] = mapped_column(Boolean, default=False)
    motion_threshold: Mapped[int] = mapped_column(Integer, default=500)
    continuous_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
