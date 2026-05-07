from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.schedule import RecordingSchedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("/camera/{camera_id}", response_model=list[ScheduleResponse])
async def list_schedules(camera_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RecordingSchedule).where(RecordingSchedule.camera_id == camera_id)
    )
    return result.scalars().all()


@router.post("/camera/{camera_id}", response_model=ScheduleResponse, status_code=201)
async def create_schedule(camera_id: int, body: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    schedule = RecordingSchedule(camera_id=camera_id, **body.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, body: ScheduleUpdate, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(RecordingSchedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    schedule = await db.get(RecordingSchedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    await db.delete(schedule)
    await db.commit()
