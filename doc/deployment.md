# Deployment

## Requirements

- Linux host (required for `network_mode: host` used by the backend)
- Docker Engine 24+
- Docker Compose v2 (`docker compose` command)
- Ports 80 (Nginx) and 8000 (backend) must be available on the host

## Standard Docker Compose Deployment

```bash
git clone <repo-url>
cd cctv-camera-streaming
docker compose up -d
```

This builds both images and starts the containers. The first build downloads dependencies and may take a few minutes. Subsequent starts are fast.

Check service health:

```bash
docker compose ps
docker compose logs backend --follow
docker compose logs frontend --follow
```

The backend health endpoint is checked every 30 seconds:

```bash
curl http://localhost:8000/health
```

## Stopping and Restarting

```bash
docker compose down          # stop and remove containers
docker compose restart       # restart without rebuilding
docker compose up -d --build # rebuild images and restart
```

## Data Persistence

Three directories/files are bind-mounted and persist across container restarts:

| Host path | Container path | Contents |
|---|---|---|
| `./data/cctv.db` | `/app/cctv.db` | SQLite database |
| `./backend/recordings/` | `/app/recordings/` | MP4 recording files |
| `./backend/hls/` | `/app/hls/` | HLS segments (ephemeral, recreated each stream) |

Ensure the host directories exist before first run (Docker creates them automatically as root-owned directories when using bind mounts; create them manually to own them):

```bash
mkdir -p data backend/recordings backend/hls
touch data/cctv.db
```

## USB Webcams and Capture Cards

Hardware devices must be passed through explicitly. Edit `docker-compose.yml`:

```yaml
services:
  backend:
    devices:
      - /dev/video0:/dev/video0
      - /dev/video1:/dev/video1
```

Then restart:

```bash
docker compose up -d --force-recreate backend
```

Verify the device is visible inside the container:

```bash
docker compose exec backend ls -la /dev/video*
```

## Network Architecture

The backend uses `network_mode: host` so it can:
- Bind to the host's network interfaces (required for nmap and ONVIF multicast discovery)
- Access cameras on the LAN directly without NAT

The frontend container uses the default Docker bridge network and reaches the backend via the `extra_hosts` entry:

```yaml
extra_hosts:
  - "backend:host-gateway"
```

Nginx resolves `backend` to the Docker host gateway IP (typically `172.17.0.1`) and proxies `/api/` and `/hls/` to `http://backend:8000`.

## Exposing to a LAN or Internet

The frontend is already accessible on the host's port 80. To expose on a specific interface only, add the IP binding:

```yaml
ports:
  - "192.168.1.50:80:80"
```

For HTTPS / external access, place a reverse proxy (Nginx, Caddy, Traefik) in front of port 80 that handles TLS termination. The application itself has no TLS configuration.

## Disk Space Management

Recording files accumulate in `backend/recordings/`. There is no automatic cleanup. Use a cron job on the host:

```bash
# Delete recordings older than 30 days
find /path/to/cctv-camera-streaming/backend/recordings -name "*.mp4" -mtime +30 -delete
```

HLS segments are managed by FFmpeg and stay small (at most `HLS_LIST_SIZE × HLS_SEGMENT_TIME` seconds of data per camera).

## Rebuilding After Code Changes

```bash
docker compose up -d --build
```

To rebuild only one service:

```bash
docker compose build backend
docker compose up -d --no-deps backend
```

## Logs

```bash
docker compose logs -f backend   # FFmpeg output is suppressed; shows Python logs
docker compose logs -f frontend  # Nginx access logs
```

Backend log level is `INFO` by default (set in `main.py`). To increase verbosity, add `logging.basicConfig(level=logging.DEBUG)` or set the `LOG_LEVEL` environment variable if you add pydantic-settings support for it.

## Container Resource Usage

Each active FFmpeg stream process consumes CPU proportional to the number of cameras and whether transcoding is needed:

- RTSP cameras with `-c:v copy` use minimal CPU (no transcoding)
- USB webcams and capture cards with `-c:v libx264 -preset ultrafast` use more CPU

Monitor with:

```bash
docker stats
```
