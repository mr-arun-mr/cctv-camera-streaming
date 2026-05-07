# Motion Detection

## Overview

Motion detection runs per camera as a background daemon thread. It reads frames from the camera source using OpenCV, applies a frame-differencing algorithm to measure pixel change area, and triggers recording when movement exceeds a configurable threshold.

## Algorithm

The detector uses a classic background subtraction approach based on absolute frame difference:

```
Frame N (grayscale + blur)
    │
    ▼
absdiff(Frame N, Frame N-1)
    │
    ▼
Threshold (binary, level=25)
    │
    ▼
Find contours
    │
    ▼
Sum contour areas  →  motion_area
    │
    ├── motion_area > threshold  →  motion detected
    └── motion_area ≤ threshold  →  no motion
```

### Step-by-step

1. **Capture frame** from `cv2.VideoCapture` (10 fps polling, 0.1 s sleep)
2. **Convert to grayscale** — `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`
3. **Gaussian blur** — `cv2.GaussianBlur(gray, (21, 21), 0)` — suppresses noise and minor pixel fluctuations
4. **Absolute difference** — `cv2.absdiff(prev_gray, gray)` — highlights pixels that changed
5. **Binary threshold** — `cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)` — any change greater than 25/255 intensity counts
6. **Contour detection** — `cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
7. **Area sum** — sum of `cv2.contourArea(c)` for all contours
8. Compare area sum to `camera.motion_threshold`

## Configuration

| Parameter | Source | Default | Description |
|---|---|---|---|
| `motion_threshold` | `Camera.motion_threshold` | 500 | Minimum pixel-area sum to count as motion |
| `MOTION_COOLDOWN_SECONDS` | Environment variable | 30 | Seconds to continue recording after motion stops |

### Threshold guidance

| Scene | Suggested threshold |
|---|---|
| Indoor, small movements | 200–500 |
| Outdoor, wind/trees | 2000–5000 |
| Low-light, noisy sensor | 1000–3000 |
| Only large objects | 5000+ |

A threshold that is too low will trigger on lighting changes or camera noise. A threshold that is too high will miss small or distant movements.

## Cooldown

After motion is no longer detected, recording continues for `MOTION_COOLDOWN_SECONDS` before stopping. This prevents rapid start/stop cycles when motion is intermittent. The `motion_end_time` is updated on every frame where motion is detected:

```python
if motion_area > threshold:
    motion_end_time = now + cooldown   # extend the window
    # start recording if not already active

elif now > motion_end_time and is_recording:
    # stop recording
```

## Thread Model

Each camera runs one daemon thread (`threading.Thread(daemon=True)`). A `threading.Event` is used as the stop flag.

```python
_threads: dict[int, threading.Thread]   # camera_id → thread
_stop_flags: dict[int, threading.Event] # camera_id → stop event
```

The thread owns its own `asyncio` event loop for calling async recorder functions:

```python
loop = asyncio.new_event_loop()
loop.run_until_complete(_start_rec())
```

## Recording Integration

The motion detector depends on the `recorder` module (injected at startup via `configure()` to avoid circular imports):

- **Start recording**: calls `recorder.start(camera_id, source, "motion", db)` wrapped in `AsyncSessionLocal()`
- **Stop recording**: calls `recorder.stop(camera_id, db)`
- **Guard**: only starts if `not recorder.is_recording(camera_id)`

## Source Reconnection

If the camera goes offline (`cap.read()` returns `ret=False`), the thread sleeps 1 second and then reopens `VideoCapture`. This is a simple retry loop without backoff.

## Enabling Motion Detection

1. Set `Camera.motion_detection = true` via `PUT /api/cameras/{id}`
2. The motion detector starts automatically at application startup for all enabled cameras with `motion_detection=true`
3. To start at runtime (after enabling on an existing camera), the camera must be updated via the API — the router re-reads the camera and starts the detector

Note: the current implementation starts the motion detector at application boot only. Enabling it on a running camera requires a service restart or API call that explicitly starts the detector. The Cameras page in the UI handles this by issuing a start call when toggling the flag.

## Stopping Motion Detection

- `DELETE /api/cameras/{id}` — stops the detector as part of camera deletion
- `motion_detector.stop(camera_id)` — called directly in the cameras router
- `motion_detector.stop_all()` — called during application shutdown

## Limitations

- Frame-differencing is sensitive to global illumination changes (e.g. lights turning on, headlights sweeping across a scene)
- The 10 fps poll rate is a balance between CPU usage and detection responsiveness — small fast objects moving between frames may be missed
- The `(21, 21)` blur kernel smooths out noise but may merge nearby motion regions, affecting the threshold interpretation
- No background modelling or adaptive thresholding; the algorithm compares successive frames, not a static background model
