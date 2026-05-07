# Live HLS Streaming

## Overview

Each camera streams live video via HTTP Live Streaming (HLS). FFmpeg reads the camera source (RTSP or V4L2) and writes a rolling window of MPEG-TS segments plus an M3U8 playlist to disk. The browser fetches the playlist and segments directly via HTTP.

## Pipeline

```
Camera source
  │
  ▼
FFmpeg process (one per camera)
  │  reads RTSP over TCP  or  V4L2 device
  │  segments video into .ts files (HLS_SEGMENT_TIME seconds each)
  │  maintains rolling .m3u8 playlist (HLS_LIST_SIZE entries)
  │  deletes old segments automatically (hls_flags=delete_segments)
  ▼
/app/hls/<camera_id>/
  ├── stream.m3u8
  ├── stream0.ts
  ├── stream1.ts
  └── ...
  │
  ▼  (FastAPI StaticFiles mount at /hls)
GET /hls/<camera_id>/stream.m3u8
  │
  ▼  (Nginx proxy)
Browser HLS.js
  │  polls playlist every segment duration
  │  fetches new .ts segments
  ▼
<video> element
```

## FFmpeg Commands

### RTSP cameras (IP, ONVIF, DVR channels)

```bash
ffmpeg -y \
  -rtsp_transport tcp \
  -i rtsp://user:pass@ip:554/stream \
  -c:v copy \
  -c:a aac \
  -f hls \
  -hls_time 2 \
  -hls_list_size 5 \
  -hls_flags delete_segments \
  /app/hls/<id>/stream.m3u8
```

`-c:v copy` passes through the video stream without re-encoding (no CPU overhead). Audio is transcoded to AAC for browser compatibility.

### USB webcams and capture cards (V4L2)

```bash
ffmpeg -y \
  -f v4l2 \
  -i /dev/video<N> \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -c:a aac \
  -f hls \
  -hls_time 2 \
  -hls_list_size 5 \
  -hls_flags delete_segments \
  /app/hls/<id>/stream.m3u8
```

`-preset ultrafast -tune zerolatency` minimises encoding latency at the cost of compression efficiency.

## Watchdog

An async background task (`stream_manager._watchdog`) polls all registered streams every 10 seconds. If a process has exited (e.g. camera went offline), it is automatically restarted using the same source configuration. This provides passive resilience without requiring user intervention.

## Stream Lifecycle

1. `POST /api/stream/{id}/start` → `stream_manager.start(camera_id, source)`
   - Builds FFmpeg command
   - Spawns subprocess with stdout/stderr suppressed
   - Records `started_at` timestamp
   - Registers source in `_camera_sources` for watchdog

2. Stream runs; FFmpeg continually writes/deletes `.ts` files and updates `stream.m3u8`

3. `POST /api/stream/{id}/stop` → `stream_manager.stop(camera_id)`
   - Sends `SIGTERM` to the FFmpeg process
   - Waits up to 5 seconds, then `SIGKILL`
   - Deletes all files in `/app/hls/<id>/`
   - Removes from watchdog registry

## Browser Playback (VideoPlayer)

The `VideoPlayer` React component:

1. Constructs the HLS URL: `/hls/{cameraId}/stream.m3u8`
2. Creates an `Hls` instance with `lowLatencyMode: true` and `backBufferLength: 10`
3. Calls `hls.loadSource(url)` and `hls.attachMedia(videoElement)`
4. On `MANIFEST_PARSED` event: calls `video.play()`
5. On fatal HLS error: destroys the instance and retries after 3 seconds

Safari uses native HLS support (`video.src = url`) instead of HLS.js.

## Latency

End-to-end latency is approximately:

```
latency ≈ HLS_SEGMENT_TIME × 2 + network + player buffer
         ≈ 2 × 2 + ~0.1 + ~1.5 = ~5.6 seconds (default)
```

To reduce latency, lower `HLS_SEGMENT_TIME` to 1 at the cost of more segment requests:

```
HLS_SEGMENT_TIME=1
HLS_LIST_SIZE=3
```

## Segment Storage

Segments are written to `/app/hls/<camera_id>/` which is volume-mounted to `./backend/hls/` on the host. At any time, only `HLS_LIST_SIZE` segments exist per camera (approximately `HLS_LIST_SIZE × HLS_SEGMENT_TIME × bitrate` bytes). For a 2 Mbit/s stream with defaults: `5 × 2 × 2 Mbps ÷ 8 = ~2.5 MB` per camera.

## Concurrent Stream Count

Each stream is one FFmpeg process. The practical limit depends on host CPU (for V4L2 cameras) or network bandwidth (for RTSP cameras). RTSP cameras with `-c:v copy` use ~1–5% CPU each on modern hardware; V4L2 cameras with libx264 use ~10–30% CPU depending on resolution.
