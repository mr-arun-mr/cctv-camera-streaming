# CCTV Camera Streaming

A self-hosted, web-based CCTV management platform that supports IP cameras, ONVIF devices, USB webcams, capture cards, and DVR systems. Streams live video via HLS, records on demand or by schedule, and triggers recordings automatically on motion.

## Features

- **Live HLS Streaming** — Low-latency HTTP Live Streaming for all camera types, playable in any modern browser
- **Multi-source Support** — IP cameras (RTSP), ONVIF, USB webcams, V4L2 capture cards, DVR channels
- **Video Recording** — Manual, continuous, scheduled, and motion-triggered recording to MP4
- **Motion Detection** — Frame-differencing with OpenCV, configurable sensitivity, automatic cooldown
- **Scheduled Recording** — Day-of-week and time-range schedules via APScheduler
- **Device Discovery** — LAN port scan, ONVIF WS-Discovery, local webcam enumeration, DVR channel probing
- **Web UI** — React + TypeScript SPA with live grid, camera management, recording browser, and discovery

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Linux host (required for `network_mode: host` used by the backend)

### Run

```bash
git clone <repo-url>
cd cctv-camera-streaming
docker compose up -d
```

Open `http://localhost` in your browser.

### USB Webcams / Capture Cards

Uncomment and adjust the `devices` block in `docker-compose.yml`:

```yaml
services:
  backend:
    devices:
      - /dev/video0:/dev/video0
      - /dev/video1:/dev/video1
```

## Project Structure

```
cctv-camera-streaming/
├── README.md
├── docker-compose.yml
├── data/                    # SQLite database (gitignored at runtime)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── ffmpeg-static        # Embedded FFmpeg binary
│   ├── ffprobe-static       # Embedded FFprobe binary
│   └── app/
│       ├── main.py          # FastAPI app, lifespan, routing
│       ├── config.py        # Settings (env-based)
│       ├── database.py      # SQLAlchemy async setup
│       ├── models/          # ORM models: Camera, RecordingSession, RecordingSchedule
│       ├── routers/         # API routes: cameras, stream, recording, schedule, scanner
│       ├── schemas/         # Pydantic request/response schemas
│       └── services/        # Business logic: stream_manager, recorder, motion_detector, scheduler, scanners
└── frontend/
    ├── Dockerfile
    ├── nginx.conf           # Reverse proxy config
    └── src/
        ├── App.tsx          # Root layout and routing
        ├── types/           # TypeScript interfaces
        ├── store/           # Zustand state
        ├── api/             # Axios API clients
        ├── components/      # CameraGrid, CameraCard, VideoPlayer
        └── pages/           # Dashboard, Cameras, Discover, Recordings
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](doc/architecture.md) | System design, data flow, component interaction |
| [Backend](doc/backend.md) | Python/FastAPI service internals |
| [Frontend](doc/frontend.md) | React/TypeScript UI internals |
| [API Reference](doc/api.md) | Full REST API endpoint reference |
| [Configuration](doc/configuration.md) | Environment variables and tuning |
| [Deployment](doc/deployment.md) | Docker, volumes, networking |
| [HLS Streaming](doc/features/streaming.md) | Live stream pipeline |
| [Recording](doc/features/recording.md) | Recording types and storage |
| [Motion Detection](doc/features/motion-detection.md) | OpenCV pipeline and settings |
| [Scheduling](doc/features/scheduling.md) | Time-based recording schedules |
| [Device Discovery](doc/features/device-discovery.md) | Network scan, ONVIF, webcam, DVR |

## Technology Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy (async) |
| Video processing | FFmpeg (static binary) |
| Computer vision | OpenCV (headless) |
| Job scheduling | APScheduler |
| Camera protocols | ONVIF (onvif-zeep), RTSP |
| Network scanning | psutil + async TCP probing |
| Frontend framework | React 18 + TypeScript |
| Build tool | Vite |
| Styling | Tailwind CSS + Radix UI |
| Video playback | HLS.js |
| State management | Zustand + TanStack Query |
| Containerisation | Docker + Nginx |

## Default Ports

| Service | Port |
|---|---|
| Web UI (Nginx) | 80 |
| Backend API (Uvicorn) | 8000 (host network) |
