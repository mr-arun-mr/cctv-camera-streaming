# API Reference

Base URL: `http://localhost:8000` (or via Nginx proxy at `/api/` on port 80).

All request and response bodies are JSON. Timestamps are ISO 8601 UTC strings.

---

## Health

### GET /health

Returns `200 OK` when the service is running.

**Response**
```json
{ "status": "ok" }
```

---

## Cameras

### GET /api/cameras/

List all cameras ordered by ID.

**Response** `200` — array of Camera objects

```json
[
  {
    "id": 1,
    "name": "Front Door",
    "ip_address": "192.168.1.100",
    "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
    "device_index": null,
    "device_path": null,
    "username": "admin",
    "password": "pass",
    "camera_type": "ip",
    "dvr_host": null,
    "channel_number": null,
    "dvr_brand": null,
    "enabled": true,
    "motion_detection": false,
    "motion_threshold": 500,
    "continuous_recording": false,
    "created_at": "2024-01-01T12:00:00"
  }
]
```

---

### POST /api/cameras/

Create a camera.

**Request body**

```json
{
  "name": "Front Door",
  "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
  "camera_type": "ip",
  "enabled": true,
  "motion_detection": false,
  "motion_threshold": 500,
  "continuous_recording": false
}
```

`camera_type` values: `onvif` | `ip` | `rtsp` | `webcam` | `usb_capture` | `dvr_channel`

**Response** `201` — Camera object

---

### GET /api/cameras/{camera_id}

Get a single camera.

**Response** `200` Camera | `404` not found

---

### PUT /api/cameras/{camera_id}

Update a camera. Only provided fields are changed (partial update).

**Response** `200` Camera | `404` not found

---

### DELETE /api/cameras/{camera_id}

Delete a camera. Also stops its active stream and motion detector.

**Response** `204` | `404`

---

### POST /api/cameras/{camera_id}/test

Test camera connectivity.

- For `webcam`/`usb_capture`: opens with `cv2.VideoCapture`, measures latency
- For all others: runs `ffprobe` against `rtsp_url`, measures latency

**Response** `200`

```json
{ "ok": true, "latency_ms": 87, "error": null }
```

```json
{ "ok": false, "latency_ms": null, "error": "Connection timed out" }
```

---

## Streaming

### POST /api/stream/{camera_id}/start

Start HLS streaming for a camera. Spawns an FFmpeg process that writes segments to `/app/hls/{camera_id}/`.

**Response** `200`
```json
{ "status": "started" }
```

`400` if the camera is disabled. `500` if FFmpeg fails to start.

---

### POST /api/stream/{camera_id}/stop

Stop the HLS stream and delete segment files.

**Response** `200`
```json
{ "status": "stopped" }
```

---

### GET /api/stream/{camera_id}/status

**Response** `200`

```json
{
  "active": true,
  "started_at": "2024-01-01T12:00:00",
  "segment_count": 3
}
```

When inactive:
```json
{ "active": false, "started_at": null, "segment_count": 0 }
```

---

### GET /api/stream/active

List camera IDs with active streams.

**Response** `200`
```json
{ "camera_ids": [1, 3, 7] }
```

---

## HLS Playlists

HLS playlists and segments are served as static files, not via the API router.

| Path | Description |
|---|---|
| `GET /hls/{camera_id}/stream.m3u8` | HLS playlist |
| `GET /hls/{camera_id}/*.ts` | MPEG-TS segments |

---

## Recording

### POST /api/recording/{camera_id}/start

Start a manual recording. Returns immediately once the FFmpeg process is launched.

**Response** `200`
```json
{ "status": "started", "session_id": 42 }
```

`400` if already recording or FFmpeg fails.

---

### POST /api/recording/{camera_id}/stop

Stop the current recording. Updates the session record with end time and file size.

**Response** `200`
```json
{ "status": "stopped" }
```

---

### GET /api/recording/{camera_id}/status

**Response** `200`

Active recording:
```json
{
  "recording": true,
  "recording_type": "manual",
  "started_at": "2024-01-01T12:30:00",
  "file_path": "1_manual_20240101_123000.mp4"
}
```

Idle:
```json
{ "recording": false, "recording_type": null, "started_at": null, "file_path": null }
```

---

### GET /api/recording/files

List completed recordings. Excludes sessions where the file no longer exists on disk.

**Query params:** `skip=0`, `limit=100`

**Response** `200` — array

```json
[
  {
    "filename": "1_motion_20240101_143000.mp4",
    "camera_id": 1,
    "size_bytes": 10485760,
    "created_at": "2024-01-01T14:30:00",
    "recording_type": "motion"
  }
]
```

---

### GET /api/recording/files/{filename}

Download a recording file.

**Response** `200` `video/mp4` binary | `404` not found

---

### DELETE /api/recording/files/{filename}

Delete the file from disk and remove the database row.

**Response** `204` | `404`

---

## Schedules

### GET /api/schedule/

List all recording schedules.

**Response** `200` — array of Schedule objects

```json
[
  {
    "id": 1,
    "camera_id": 1,
    "days_of_week": "[0,1,2,3,4]",
    "start_time": "08:00",
    "end_time": "18:00",
    "enabled": true
  }
]
```

`days_of_week` is a JSON-encoded array of integers where 0=Monday, 6=Sunday.

---

### POST /api/schedule/

Create a schedule.

**Request body**

```json
{
  "camera_id": 1,
  "days_of_week": "[0,1,2,3,4]",
  "start_time": "08:00",
  "end_time": "18:00",
  "enabled": true
}
```

**Response** `201` — Schedule object

---

### PUT /api/schedule/{schedule_id}

Update a schedule.

**Response** `200` | `404`

---

### DELETE /api/schedule/{schedule_id}

Delete a schedule.

**Response** `204` | `404`

---

## Scanner

### POST /api/scan/network

Start an async LAN port scan. Returns immediately with a `job_id` to poll.

**Response** `200`
```json
{ "job_id": "550e8400-e29b-41d4-a716-446655440000" }
```

---

### GET /api/scan/network/{job_id}

Poll the scan job.

**Response** `200`

While running:
```json
{ "status": "running", "results": [] }
```

On completion:
```json
{
  "status": "done",
  "results": [
    { "ip": "192.168.1.100", "open_ports": [554, 80], "hostname": "camera1.local", "mac": "" }
  ]
}
```

`404` if job_id not found.

---

### POST /api/scan/onvif

Run ONVIF WS-Discovery. Blocks for up to 5 seconds.

**Response** `200` — array

```json
[
  {
    "ip": "192.168.1.101",
    "xaddr": "http://192.168.1.101/onvif/device_service",
    "manufacturer": "Hikvision",
    "model": "DS-2CD2143G2-I",
    "rtsp_url": ""
  }
]
```

---

### GET /api/scan/webcams

Enumerate local V4L2 devices `/dev/video0`–`/dev/video9`.

**Response** `200`

```json
[
  {
    "device_index": 0,
    "device_path": "/dev/video0",
    "width": 1920,
    "height": 1080,
    "name": "USB 2.0 Camera",
    "is_capture_card": false
  }
]
```

---

### POST /api/scan/dvr

Probe a DVR for active channels.

**Request body**

```json
{
  "ip": "192.168.1.200",
  "username": "admin",
  "password": "admin",
  "brand": "hikvision",
  "channel_count": 16
}
```

`brand` values: `hikvision` | `dahua` | `uniview` | `generic`

**Response** `200`

```json
{
  "ip": "192.168.1.200",
  "brand": "hikvision",
  "channels": [
    { "channel": 1, "rtsp_url": "rtsp://admin:admin@192.168.1.200:554/Streaming/Channels/0101", "name": "Channel 1" },
    { "channel": 2, "rtsp_url": "rtsp://admin:admin@192.168.1.200:554/Streaming/Channels/0201", "name": "Channel 2" }
  ]
}
```

---

### POST /api/scan/dvr/add-all

Bulk-create Camera records from DVR channel probe results.

**Request body**

```json
{
  "channels": [
    { "channel": 1, "rtsp_url": "rtsp://...", "name": "Channel 1" }
  ],
  "dvr_host": "192.168.1.200",
  "brand": "hikvision",
  "username": "admin",
  "password": "admin"
}
```

**Response** `201`
```json
{ "created": 2 }
```

---

### POST /api/scan/probe

Probe a single IP for RTSP streams by trying common URL patterns.

**Request body**

```json
{
  "ip": "192.168.1.100",
  "port": 554,
  "username": "admin",
  "password": "pass"
}
```

**Response** `200`

```json
{ "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/", "reachable": true }
```

```json
{ "rtsp_url": null, "reachable": false }
```

---

## Error Responses

All endpoints return standard HTTP error codes with a JSON body:

```json
{ "detail": "Camera not found" }
```

| Code | Meaning |
|---|---|
| 400 | Bad request (e.g. camera disabled, already recording) |
| 404 | Resource not found |
| 500 | Internal server error (e.g. FFmpeg failed to launch) |
