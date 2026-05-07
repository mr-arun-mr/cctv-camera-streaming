# Architecture

## Overview

The system is split into two containers that communicate over the host network. The backend is a Python async service; the frontend is a static React build served by Nginx which also proxies API calls.

```
Browser
  │
  ▼
Nginx :80
  ├── /api/*  ──────────────────► FastAPI :8000
  ├── /hls/*  ──────────────────► FastAPI :8000 (StaticFiles)
  └── /*  (SPA fallback)
```

## Container Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Host Network                                                │
│                                                              │
│  ┌─────────────────────────────┐                            │
│  │  backend  (network_mode:host)│                            │
│  │  ─────────────────────────  │                            │
│  │  FastAPI + Uvicorn :8000    │                            │
│  │  SQLite  /app/cctv.db       │                            │
│  │  FFmpeg processes (spawned) │                            │
│  │  OpenCV threads             │                            │
│  │  APScheduler jobs           │                            │
│  └─────────────────────────────┘                            │
│                                                              │
│  ┌─────────────────────────────┐                            │
│  │  frontend  :80              │                            │
│  │  ─────────────────────────  │                            │
│  │  Nginx                      │                            │
│  │    proxy /api  → backend    │                            │
│  │    proxy /hls  → backend    │                            │
│  │    serve dist/ (SPA)        │                            │
│  └─────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

## Live Stream Data Flow

```
Camera source (RTSP / V4L2)
  │
  ▼
FFmpeg process (per camera)
  │  writes .ts segments + .m3u8 playlist
  ▼
/app/hls/<camera_id>/stream.m3u8
  │
  ▼  (StaticFiles mount in FastAPI)
GET /hls/<camera_id>/stream.m3u8
  │
  ▼  (Nginx proxy)
Browser HLS.js
  │  polls playlist, fetches segments
  ▼
<video> element
```

## Recording Data Flow

```
Trigger (manual API / motion detector / scheduler)
  │
  ▼
recorder.start()
  │  spawns FFmpeg process
  │  creates RecordingSession row (status="recording")
  ▼
/app/recordings/<camera_id>_<type>_<timestamp>.mp4
  │
  ▼
recorder.stop()
  │  terminates FFmpeg
  │  updates RecordingSession (end_time, file_size, status="stopped")
  ▼
GET /api/recording/files  →  browser download or in-page playback
```

## Motion Detection Data Flow

```
motion_detector thread (per camera)
  │  reads frames from OpenCV VideoCapture
  │  computes frame diff → contour area
  │  area > threshold  AND  not already recording
  │
  ├─► recorder.start(type="motion")
  │
  │  area <= threshold  AND  cooldown expired  AND  is_recording
  │
  └─► recorder.stop()
```

## Application Startup Sequence

1. FastAPI `lifespan` begins
2. Output directories created (`/app/hls`, `/app/recordings`)
3. `init_db()` — SQLAlchemy creates tables if absent
4. Services wired: `motion_detector.configure(recorder, db_factory)`, `scheduler.configure(recorder, stream_manager)`
5. `stream_manager.start_watchdog()` — async task polls every 10 s to restart dead streams
6. `scheduler.start()` — APScheduler job fires every 1 minute to check schedules
7. All enabled cameras with `continuous_recording=True` start recording
8. All enabled cameras with `motion_detection=True` start motion detector threads

## Backend Module Dependencies

```
main.py
 ├── config.py          (Settings singleton)
 ├── database.py        (engine, SessionLocal, Base)
 ├── models/            (SQLAlchemy ORM)
 ├── routers/           (FastAPI APIRouter)
 │    ├── cameras.py
 │    ├── stream.py     ──► services/stream_manager.py
 │    ├── recording.py  ──► services/recorder.py
 │    ├── schedule.py   ──► models/schedule.py
 │    └── scanner.py    ──► services/network_scanner.py
 │                           services/onvif_scanner.py
 │                           services/local_webcam_scanner.py
 │                           services/dvr_prober.py
 └── services/
      ├── stream_manager.py   (FFmpeg HLS processes + watchdog)
      ├── recorder.py         (FFmpeg recording processes)
      ├── motion_detector.py  ──► services/recorder.py
      └── scheduler.py        ──► services/recorder.py
                                   services/stream_manager.py
```

## Frontend Module Dependencies

```
main.tsx
 └── App.tsx  (BrowserRouter, nav, routes)
      ├── pages/Dashboard.tsx    ──► components/CameraGrid.tsx
      │                               components/CameraCard.tsx
      │                               components/VideoPlayer.tsx
      ├── pages/Cameras.tsx      ──► api/cameras.ts, api/stream.ts, api/recording.ts
      ├── pages/Discover.tsx     ──► api/scanner.ts
      └── pages/Recordings.tsx   ──► api/recording.ts
           └── store/cameraStore.ts  (Zustand)
                └── @tanstack/react-query  (server state cache)
```

## Persistence

SQLite is the only persistent store. Three tables:

| Table | Purpose |
|---|---|
| `cameras` | Camera configuration and feature flags |
| `recording_sessions` | Individual recording run metadata |
| `recording_schedules` | Time-based schedule definitions |

The database file is volume-mounted at `/app/cctv.db` so it survives container restarts. Recording files (`.mp4`) and HLS segments (`.ts` + `.m3u8`) are also volume-mounted but HLS segments are ephemeral (deleted by FFmpeg's `hls_flags=delete_segments`).
