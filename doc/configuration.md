# Configuration

All backend configuration is read from environment variables at startup. Values can be supplied in `docker-compose.yml`, a `.env` file in the backend directory, or the shell environment.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:////app/cctv.db` | SQLAlchemy async database URL |
| `HLS_DIR` | `/app/hls` | Directory where FFmpeg writes HLS segments and playlists |
| `RECORDINGS_DIR` | `/app/recordings` | Directory where FFmpeg writes MP4 recordings |
| `HLS_SEGMENT_TIME` | `2` | HLS segment duration in seconds |
| `HLS_LIST_SIZE` | `5` | Number of segments kept in the HLS playlist |
| `MOTION_COOLDOWN_SECONDS` | `30` | Seconds to keep recording after motion stops |
| `SCAN_TIMEOUT_SECONDS` | `30` | Unused reserved timeout for scanner operations |

## HLS Tuning

**`HLS_SEGMENT_TIME`** — lower values reduce live latency but increase HTTP request frequency and file system writes. Values below 1 are not recommended. The default of 2 gives approximately 6–10 seconds of end-to-end latency (3×segment + buffering).

**`HLS_LIST_SIZE`** — how many `.ts` segments are kept in the playlist. Segments older than this are deleted by FFmpeg (`hls_flags=delete_segments`). `HLS_LIST_SIZE × HLS_SEGMENT_TIME` is the seekable window. The default (5×2=10 s) is intentionally small since this is a live monitor, not a DVR.

## Motion Detection Tuning

**`MOTION_COOLDOWN_SECONDS`** — after motion is no longer detected, recording continues for this many seconds before stopping. Set higher for scenes where motion is intermittent (e.g. 60–120 s).

Per-camera sensitivity is controlled by `motion_threshold` on the Camera model (default 500). This is the minimum total contour pixel area that counts as motion. Higher values ignore smaller movements.

## Database URL

The default SQLite URL uses `aiosqlite` for async I/O. To switch to PostgreSQL (not officially supported but structurally straightforward):

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
```

Add `asyncpg` to `requirements.txt` if doing so.

## Volume Paths

These paths are set inside the container. To change the host-side mount point, edit the left side of the `volumes` entry in `docker-compose.yml`:

```yaml
volumes:
  - ./backend/recordings:/app/recordings   # host:container
  - ./backend/hls:/app/hls
  - ./data/cctv.db:/app/cctv.db
```

## USB Device Passthrough

To pass USB webcams or capture cards into the backend container, uncomment and adjust the `devices` section:

```yaml
services:
  backend:
    devices:
      - /dev/video0:/dev/video0
      - /dev/video1:/dev/video1
```

Pass only specific devices, not the entire `/dev` tree.

## Local Development (Without Docker)

Create a `.env` file in `backend/`:

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./cctv.db
HLS_DIR=./hls
RECORDINGS_DIR=./recordings
HLS_SEGMENT_TIME=2
HLS_LIST_SIZE=5
MOTION_COOLDOWN_SECONDS=30
```

Then run:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For the frontend dev server:

```bash
cd frontend
npm install
npm run dev    # starts on :5173, proxies /api to :8000 via vite.config.ts
```
