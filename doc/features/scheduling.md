# Scheduled Recording

## Overview

Recording schedules define time windows during which cameras should record automatically. A schedule specifies which days of the week and what time range to record. The scheduler checks all active schedules every minute and starts or stops recordings accordingly.

## Schedule Model

A schedule belongs to one camera.

| Field | Type | Description |
|---|---|---|
| `camera_id` | Integer | FK to Camera |
| `days_of_week` | String | JSON array of integers: 0=Mon, 1=Tue, ..., 6=Sun |
| `start_time` | String | Start time in `HH:MM` 24-hour format |
| `end_time` | String | End time in `HH:MM` 24-hour format |
| `enabled` | Boolean | Whether this schedule is active |

### Example

Record camera 1 on weekdays from 08:00 to 18:00:

```json
{
  "camera_id": 1,
  "days_of_week": "[0,1,2,3,4]",
  "start_time": "08:00",
  "end_time": "18:00",
  "enabled": true
}
```

## Scheduler Implementation

The scheduler uses APScheduler's `AsyncIOScheduler` with a single interval job:

```python
_scheduler.add_job(_check_schedules, "interval", minutes=1, id="schedule_checker")
```

`_check_schedules()` runs every minute and:

1. Queries all enabled `RecordingSchedule` rows joined with enabled `Camera` rows
2. For each schedule, checks if `current_weekday in days` and `start_time <= HH:MM < end_time`
3. If in window and not recording → calls `recorder.start(type="scheduled")`
4. If outside window and recording → calls `recorder.stop()`

## Precision

The scheduler fires every minute, so recordings start and stop within approximately 1 minute of the scheduled time. For exact timing, reduce the interval (at the cost of more database queries):

```python
_scheduler.add_job(_check_schedules, "interval", seconds=30, id="schedule_checker")
```

This is not configurable via environment variables in the current implementation.

## Interaction with Other Recording Types

The scheduler calls `recorder.is_recording(camera_id)` before starting. If a manual or motion recording is already active, the scheduler will not start a new one. When the window ends, the scheduler stops the recording regardless of how it was started (it only checks `is_recording()`).

## API

### Create a schedule

```
POST /api/schedule/
{
  "camera_id": 1,
  "days_of_week": "[0,1,2,3,4]",
  "start_time": "08:00",
  "end_time": "18:00",
  "enabled": true
}
```

### List schedules

```
GET /api/schedule/
```

### Update a schedule

```
PUT /api/schedule/{id}
{ "enabled": false }
```

### Delete a schedule

```
DELETE /api/schedule/{id}
```

## Multiple Schedules per Camera

A camera can have multiple schedules (e.g. different schedules for weekdays and weekends). Each is evaluated independently each minute.

## Midnight Spanning

Schedules that cross midnight (e.g. `start_time="22:00"`, `end_time="06:00"`) are **not** directly supported by the `start_time <= HH:MM < end_time` comparison. To record overnight, create two schedules:
- `start_time="22:00"`, `end_time="23:59"`
- `start_time="00:00"`, `end_time="06:00"`

## Timezone

The scheduler uses the system clock of the container (UTC by default in Docker). Ensure the container timezone matches your intended schedule timezone by setting `TZ` in the environment if needed:

```yaml
environment:
  - TZ=Europe/London
```
