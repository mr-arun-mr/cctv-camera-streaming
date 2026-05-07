from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RecordingSchedule(Base):
    __tablename__ = "recording_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"))
    days_of_week: Mapped[str] = mapped_column(String, default="[0,1,2,3,4]")  # JSON array Mon=0
    start_time: Mapped[str] = mapped_column(String, nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String, nullable=False)    # HH:MM
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
