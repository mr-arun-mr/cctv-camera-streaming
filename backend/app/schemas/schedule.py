from pydantic import BaseModel


class ScheduleBase(BaseModel):
    days_of_week: str = "[0,1,2,3,4]"
    start_time: str
    end_time: str
    enabled: bool = True


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    days_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    enabled: bool | None = None


class ScheduleResponse(ScheduleBase):
    id: int
    camera_id: int

    model_config = {"from_attributes": True}
