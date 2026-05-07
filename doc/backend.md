# Backend

The backend is a Python 3.11 async web service built on FastAPI. It manages camera configurations in SQLite, spawns FFmpeg child processes for streaming and recording, runs OpenCV motion detection in background threads, and schedules jobs with APScheduler.

## Entry Point

`backend/app/main.py`

FastAPI is instantiated with a `lifespan` context manager that handles startup and shutdown:

```python
app = FastAPI(title="CCTV Camera Streaming", version="1.0.0", lifespan=lifespan)
```

On startup the lifespan:
- Creates output directories
- Initialises the database schema
- Wires service dependencies (avoids circular imports)
- Starts the stream watchdog and scheduler
- Auto-starts continuous recording and motion detection for all enabled cameras

On shutdown it stops all streams, motion detectors, and the scheduler cleanly.

## Configuration

`backend/app/config.py` — `pydantic_settings.BaseSettings`

All settings are read from environment variables (or a `.env` file). See [Configuration](configuration.md) for the full reference.

```python
from app.config import settings

settings.hls_dir          # "/app/hls"
settings.recordings_dir   # "/app/recordings"
settings.hls_path(cam_id) # Path("/app/hls/<cam_id>")
```

## Database

`backend/app/database.py`

- Engine: `create_async_engine` with `aiosqlite`
- Session factory: `async_sessionmaker` exposed as `AsyncSessionLocal`
- `Base`: declarative base for all models
- `init_db()`: calls `Base.metadata.create_all`
- `get_db()`: FastAPI dependency that yields a session and commits on success

## Models

### Camera (`models/camera.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String | Display name |
| `ip_address` | String nullable | For IP/ONVIF cameras |
| `rtsp_url` | String nullable | Full RTSP URL |
| `device_index` | Integer nullable | `/dev/videoN` index |
| `device_path` | String nullable | `/dev/video0` path string |
| `username` | String nullable | Camera credentials |
| `password` | String nullable | |
| `camera_type` | String | `onvif`, `ip`, `rtsp`, `webcam`, `usb_capture`, `dvr_channel` |
| `dvr_host` | String nullable | DVR IP address |
| `channel_number` | Integer nullable | DVR channel |
| `dvr_brand` | String nullable | `hikvision`, `dahua`, etc. |
| `enabled` | Boolean | Master switch |
| `motion_detection` | Boolean | Enable motion detector |
| `motion_threshold` | Integer | Pixel-area threshold (default 500) |
| `continuous_recording` | Boolean | Record always when enabled |
| `created_at` | DateTime | Server default |

### RecordingSession (`models/recording.py`)

Tracks each individual recording run.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `camera_id` | Integer FK | |
| `file_path` | String | Filename relative to `recordings_dir` |
| `recording_type` | String | `manual`, `continuous`, `motion`, `scheduled` |
| `status` | String | `recording`, `stopped`, `error` |
| `start_time` | DateTime | |
| `end_time` | DateTime nullable | Filled on stop |
| `file_size` | Integer nullable | Bytes, filled on stop |

### RecordingSchedule (`models/schedule.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `camera_id` | Integer FK | |
| `days_of_week` | String | JSON array of integers, 0=Mon…6=Sun |
| `start_time` | String | `HH:MM` |
| `end_time` | String | `HH:MM` |
| `enabled` | Boolean | |

## Routers

All routers share the `/api` prefix. Dependencies inject `AsyncSession` via `Depends(get_db)`.

### cameras (`/api/cameras`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | List all cameras |
| POST | `/` | Create camera |
| GET | `/{id}` | Get camera |
| PUT | `/{id}` | Update camera |
| DELETE | `/{id}` | Delete camera + stop its stream/motion |
| POST | `/{id}/test` | Test connectivity via ffprobe or OpenCV |

### stream (`/api/stream`)

| Method | Path | Description |
|---|---|---|
| POST | `/{id}/start` | Start HLS stream |
| POST | `/{id}/stop` | Stop HLS stream |
| GET | `/{id}/status` | Stream status (active, started_at, segment_count) |
| GET | `/active` | List active camera IDs |

### recording (`/api/recording`)

| Method | Path | Description |
|---|---|---|
| POST | `/{id}/start` | Start manual recording |
| POST | `/{id}/stop` | Stop recording |
| GET | `/{id}/status` | Recording status |
| GET | `/files` | List completed recordings |
| GET | `/files/{filename}` | Download MP4 |
| DELETE | `/files/{filename}` | Delete file + DB row |

### schedule (`/api/schedule`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | List schedules |
| POST | `/` | Create schedule |
| PUT | `/{id}` | Update schedule |
| DELETE | `/{id}` | Delete schedule |

### scanner (`/api/scan`)

| Method | Path | Description |
|---|---|---|
| POST | `/network` | Start async LAN scan, returns `job_id` |
| GET | `/network/{job_id}` | Poll scan result |
| POST | `/onvif` | Run ONVIF WS-Discovery |
| GET | `/webcams` | Enumerate local V4L2 devices |
| POST | `/dvr` | Probe DVR channels by brand pattern |
| POST | `/dvr/add-all` | Bulk-create cameras from DVR channels |
| POST | `/probe` | Probe a specific IP for RTSP streams |

## Services

### stream_manager (`services/stream_manager.py`)

Module-level dictionaries hold process handles and metadata:

```
_processes: dict[int, Popen]       # camera_id → process
_started_at: dict[int, datetime]   # camera_id → start time
_camera_sources: dict[int, dict]   # camera_id → source config
```

**`start(camera_id, source)`** — builds and spawns FFmpeg command, registers process.

FFmpeg command for RTSP cameras:
```
ffmpeg -y -rtsp_transport tcp -i <rtsp_url>
  -c:v copy -c:a aac
  -f hls -hls_time 2 -hls_list_size 5 -hls_flags delete_segments
  /app/hls/<id>/stream.m3u8
```

FFmpeg command for V4L2 (webcam/capture card):
```
ffmpeg -y -f v4l2 -i /dev/video<N>
  -c:v libx264 -preset ultrafast -tune zerolatency -c:a aac
  -f hls -hls_time 2 -hls_list_size 5 -hls_flags delete_segments
  /app/hls/<id>/stream.m3u8
```

**`stop(camera_id)`** — terminates process, removes HLS segment files.

**`_watchdog()`** — async loop, runs every 10 seconds, restarts any process whose `poll()` returns non-None.

### recorder (`services/recorder.py`)

```
_processes: dict[int, tuple[Popen, int]]   # camera_id → (process, session_id)
```

**`start(camera_id, source, recording_type, db)`** — creates `RecordingSession` row, spawns FFmpeg.

FFmpeg command for RTSP (stream copy, no re-encode):
```
ffmpeg -y -rtsp_transport tcp -i <rtsp_url> -c copy <output.mp4>
```

FFmpeg command for V4L2 (encode to H.264):
```
ffmpeg -y -f v4l2 -i /dev/video<N> -c:v libx264 -preset fast -c:a aac <output.mp4>
```

Output filename pattern: `<camera_id>_<type>_<YYYYMMDD_HHMMSS>.mp4`

**`stop(camera_id, db)`** — terminates process, updates session with `end_time`, `file_size`, `status="stopped"`.

### motion_detector (`services/motion_detector.py`)

One daemon thread per camera. Uses OpenCV `VideoCapture` to read frames at ~10 fps.

Detection pipeline per frame:
1. Convert to grayscale
2. Gaussian blur (21×21 kernel)
3. `absdiff` with previous frame
4. Binary threshold at 25
5. Find contours, sum areas
6. If total area > threshold → motion detected

On motion start: calls `recorder.start(type="motion")` via a per-thread asyncio event loop.
On motion end (after cooldown expires): calls `recorder.stop()`.

### scheduler (`services/scheduler.py`)

APScheduler `AsyncIOScheduler` with a single `interval` job that fires every minute.

`_check_schedules()` queries all enabled schedules joined with enabled cameras, checks current weekday and `HH:MM` against each schedule's window, then starts or stops recording accordingly.

### network_scanner (`services/network_scanner.py`)

Async TCP port probing (no external tools). Detects subnet from `psutil.net_if_addrs()`, then concurrently probes ports 554, 8554, 8080, 80 across the /24 subnet in batches of 50 hosts.

### onvif_scanner (`services/onvif_scanner.py`)

Uses `wsdiscovery` for WS-Discovery multicast (UDP 3702). Filters services by ONVIF scope. Extracts IP, manufacturer, and model from scope URIs. Optionally fetches RTSP URL via `onvif-zeep` WSDL.

### local_webcam_scanner (`services/local_webcam_scanner.py`)

Iterates `/dev/video0` through `/dev/video9` using OpenCV `VideoCapture`. Uses `v4l2-ctl` to read device name and detect capture cards (checks for composite/HDMI/S-Video inputs).

### dvr_prober (`services/dvr_prober.py`)

Probes DVR channels via ffprobe against brand-specific RTSP URL patterns:

| Brand | URL pattern |
|---|---|
| hikvision | `rtsp://.../Streaming/Channels/{ch:02d}01` |
| dahua | `rtsp://.../cam/realmonitor?channel={ch}&subtype=0` |
| uniview | `rtsp://.../unicast/c{ch}/s0/live` |
| generic | Several patterns tried in order |

Concurrently probes all channels (up to `channel_count`, default 16) and returns those that respond to ffprobe.

## FFmpeg Binaries

Static FFmpeg and FFprobe binaries are embedded directly in `backend/ffmpeg-static` and `backend/ffprobe-static`. The Dockerfile copies them into `$PATH`. This avoids the need for system package installation and ensures version consistency.
