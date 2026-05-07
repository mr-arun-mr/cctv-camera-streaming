# Recording

## Overview

The recording subsystem captures video from any camera source to MP4 files on disk. Four recording modes are supported: manual, continuous, motion-triggered, and scheduled. Each recording run is tracked in the `recording_sessions` database table.

## Recording Types

| Type | Trigger | Description |
|---|---|---|
| `manual` | `POST /api/recording/{id}/start` | User-initiated via API or UI |
| `continuous` | Application startup | Runs as long as the camera is enabled |
| `motion` | Motion detector threshold exceeded | Starts on motion, stops after cooldown |
| `scheduled` | APScheduler time window | Runs within configured day/time windows |

## FFmpeg Commands

### RTSP cameras (stream copy)

```bash
ffmpeg -y \
  -rtsp_transport tcp \
  -i rtsp://user:pass@ip:554/stream \
  -c copy \
  /app/recordings/<camera_id>_<type>_<YYYYMMDD_HHMMSS>.mp4
```

`-c copy` copies the video and audio streams without re-encoding. This is the most efficient approach and preserves the original quality and codec.

### USB webcams / capture cards (encode)

```bash
ffmpeg -y \
  -f v4l2 \
  -i /dev/video<N> \
  -c:v libx264 -preset fast \
  -c:a aac \
  /app/recordings/<camera_id>_<type>_<YYYYMMDD_HHMMSS>.mp4
```

`-preset fast` balances encoding speed and compression.

## Output Filename

```
<camera_id>_<recording_type>_<YYYYMMDD_HHMMSS>.mp4

Example: 3_motion_20240115_143022.mp4
```

## Recording Lifecycle

### Start

1. Check if already recording (return early if so)
2. Create a `RecordingSession` row with `status="recording"` and `start_time=now`
3. Spawn FFmpeg subprocess
4. Store `(process, session_id)` in `_processes[camera_id]`
5. Return `session_id`

### Stop

1. Retrieve `(process, session_id)` from `_processes`
2. Send `SIGTERM`; wait up to 10 seconds, then `SIGKILL`
3. Update `RecordingSession`: set `end_time`, `file_size` (from `os.stat`), `status="stopped"`

### On FFmpeg launch failure

The session row is updated to `status="error"` immediately.

## Database Schema

```sql
CREATE TABLE recording_sessions (
  id             INTEGER PRIMARY KEY,
  camera_id      INTEGER,
  file_path      TEXT,        -- filename relative to recordings_dir
  recording_type TEXT,        -- manual | continuous | motion | scheduled
  status         TEXT,        -- recording | stopped | error
  start_time     DATETIME,
  end_time       DATETIME,
  file_size      INTEGER      -- bytes
);
```

## Concurrent Recording

Only one recording per camera is allowed at a time. `recorder.is_recording(camera_id)` checks whether the stored process handle is still alive. Attempting to start a second recording returns `None` without error.

Recording and streaming are independent; a camera can stream (HLS) and record simultaneously using two separate FFmpeg processes.

## Storage Location

Recordings are stored in `/app/recordings/` (volume-mounted to `./backend/recordings/` on the host). There is no automatic rotation. See [Deployment — Disk Space Management](../deployment.md) for cleanup guidance.

## Accessing Recordings

### List

```
GET /api/recording/files?skip=0&limit=100
```

Returns recordings whose files still exist on disk, ordered by most recent first.

### Download / Playback

```
GET /api/recording/files/{filename}
```

Returns the MP4 as a `video/mp4` binary response. The frontend plays it in an HTML5 `<video>` element using this URL as the source.

### Delete

```
DELETE /api/recording/files/{filename}
```

Removes the file from disk and the `recording_sessions` row from the database.

## Continuous Recording

When `Camera.continuous_recording = true`, the application auto-starts recording at startup (in `main.py` lifespan). The recording runs indefinitely until:
- The camera is disabled
- `continuous_recording` is set to `false` and the camera is updated
- The container is stopped

There is no automatic file segmentation for long-running recordings. Very long recordings produce single large MP4 files. Consider using scheduled recordings for day-boundary segmentation instead.

## Interaction with Motion Detection

Motion detection and recording are coordinated through `recorder.is_recording()`:

- Motion detector starts a recording only if no recording is currently active
- Motion detector stops a recording only if it was started by motion (not manual/continuous/scheduled)

Note: the current implementation does not distinguish who started the recording when deciding to stop, so stopping is guarded only by `is_recording()` — if a manual recording is active, the motion detector will not attempt to start a new one.
