# Frontend

The frontend is a React 18 + TypeScript single-page application built with Vite and served by Nginx. It communicates with the backend exclusively via the REST API.

## Technology Stack

| Package | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI rendering |
| React Router DOM | 6.26 | Client-side routing |
| TypeScript | 5.5.3 | Static typing |
| Vite | 5.3.5 | Build tool and dev server |
| HLS.js | 1.5.13 | In-browser HLS playback |
| Zustand | 4.5.4 | Global client state |
| TanStack React Query | 5.51 | Server state caching and fetching |
| Axios | 1.7.3 | HTTP client |
| Tailwind CSS | 3.4.7 | Utility-first styling |
| Radix UI | various | Accessible headless components |
| Lucide React | 0.414 | Icon library |

## Directory Layout

```
frontend/src/
├── main.tsx              # React root, QueryClient setup
├── App.tsx               # Layout shell, nav, routes
├── index.css             # Tailwind directives, CSS variables
├── types/
│   └── index.ts          # Shared TypeScript interfaces
├── store/
│   └── cameraStore.ts    # Zustand store
├── api/
│   ├── cameras.ts        # Camera CRUD API calls
│   ├── stream.ts         # Stream control API calls
│   ├── recording.ts      # Recording API calls
│   └── scanner.ts        # Scanner API calls
├── components/
│   ├── CameraGrid.tsx    # Responsive camera grid layout
│   ├── CameraCard.tsx    # Single camera tile with controls
│   └── VideoPlayer.tsx   # HLS.js video element wrapper
└── pages/
    ├── Dashboard.tsx     # Live view (grid of streams)
    ├── Cameras.tsx       # Camera CRUD management
    ├── Discover.tsx      # Device discovery interface
    └── Recordings.tsx    # Recording file browser and player
```

## Entry Point (`main.tsx`)

Mounts React to `#root`, wraps the app in a `QueryClientProvider` with a 30-second stale time default.

## App Shell (`App.tsx`)

Renders a fixed sidebar navigation and a scrollable main content area. Navigation items:

| Route | Page | Icon |
|---|---|---|
| `/` | Dashboard | Video |
| `/cameras` | Cameras | Camera |
| `/discover` | Discover | Search |
| `/recordings` | Recordings | Film |

## TypeScript Interfaces (`types/index.ts`)

These interfaces mirror the backend Pydantic schemas and are used throughout the app:

```typescript
Camera            // Camera configuration and feature flags
StreamStatus      // { active, started_at, segment_count }
RecordingStatus   // { recording, recording_type, started_at, file_path }
RecordingFile     // { filename, camera_id, size_bytes, created_at, recording_type }
Schedule          // { id, camera_id, days_of_week, start_time, end_time, enabled }
ScanHost          // { ip, open_ports, hostname, mac }
OnvifDevice       // { ip, xaddr, manufacturer, model, rtsp_url }
WebcamDevice      // { device_index, device_path, width, height, name, is_capture_card }
DvrChannel        // { channel, rtsp_url, name }
```

## State Management

### Zustand Store (`store/cameraStore.ts`)

Lightweight client state for camera list, stream statuses, and recording statuses. Used by components that need to react to status changes across the grid.

### TanStack React Query

Used for all server-fetched data (camera list, recording files, schedules). Provides automatic background refetching, cache invalidation after mutations, and loading/error states.

## API Clients (`api/`)

All modules use a shared Axios instance with `baseURL` of `/api`. Each function maps directly to one REST endpoint.

```typescript
// api/cameras.ts
getCameras()                         → GET  /api/cameras/
createCamera(data)                   → POST /api/cameras/
updateCamera(id, data)               → PUT  /api/cameras/{id}
deleteCamera(id)                     → DELETE /api/cameras/{id}
testCamera(id)                       → POST /api/cameras/{id}/test

// api/stream.ts
startStream(id)                      → POST /api/stream/{id}/start
stopStream(id)                       → POST /api/stream/{id}/stop
getStreamStatus(id)                  → GET  /api/stream/{id}/status

// api/recording.ts
startRecording(id)                   → POST /api/recording/{id}/start
stopRecording(id)                    → POST /api/recording/{id}/stop
getRecordingStatus(id)               → GET  /api/recording/{id}/status
getRecordingFiles()                  → GET  /api/recording/files
deleteRecording(filename)            → DELETE /api/recording/files/{filename}

// api/scanner.ts
startNetworkScan()                   → POST /api/scan/network
getNetworkScan(jobId)                → GET  /api/scan/network/{jobId}
onvifScan()                          → POST /api/scan/onvif
getWebcams()                         → GET  /api/scan/webcams
probeDvr(ip, user, pass, brand, n)   → POST /api/scan/dvr
addAllDvrChannels(body)              → POST /api/scan/dvr/add-all
probeIp(ip, port, user, pass)        → POST /api/scan/probe
```

## Components

### VideoPlayer (`components/VideoPlayer.tsx`)

Wraps a `<video>` element and manages an HLS.js instance.

**Props:**
- `cameraId: number` — determines HLS playlist path `/hls/{cameraId}/stream.m3u8`
- `active: boolean` — only initialises HLS when true

**States:** `loading` | `playing` | `error`

**Behaviour:**
- If HLS.js is supported (non-Safari): creates `new Hls({ lowLatencyMode: true, backBufferLength: 10 })`, loads source, attaches to the `<video>` element.
- Safari native HLS: sets `video.src` directly.
- On fatal error: destroys the HLS instance and retries after 3 seconds.
- On unmount: calls `hls.destroy()`.

### CameraCard (`components/CameraCard.tsx`)

Single camera tile displaying:
- Camera name and type badge
- `VideoPlayer` component
- Stream start/stop button
- Record button
- Status indicators

### CameraGrid (`components/CameraGrid.tsx`)

Responsive grid of `CameraCard` components. Column count adapts to viewport width via Tailwind's responsive breakpoints.

## Pages

### Dashboard (`pages/Dashboard.tsx`)

Polls stream status for each camera every 5 seconds using React Query. Renders `CameraGrid`. Provides controls to start/stop all streams.

### Cameras (`pages/Cameras.tsx`)

CRUD interface for camera management. Uses a dialog (Radix UI `Dialog`) for create/edit forms. Displays camera type, IP, RTSP URL, and feature flag toggles.

### Discover (`pages/Discover.tsx`)

Tabbed interface (Radix UI `Tabs`) for four discovery methods:

| Tab | Backend endpoint | Description |
|---|---|---|
| Network Scan | POST `/api/scan/network` | LAN port scan with polling |
| ONVIF | POST `/api/scan/onvif` | WS-Discovery |
| Webcams | GET `/api/scan/webcams` | Local V4L2 devices |
| DVR Probe | POST `/api/scan/dvr` | DVR channel discovery |

Results display discovered devices with a one-click "Add Camera" action.

### Recordings (`pages/Recordings.tsx`)

Lists completed recordings from `GET /api/recording/files`. Each row shows filename, camera ID, size, date, and recording type. Provides download links and delete buttons. Completed recordings can be played inline via the HTML5 `<video>` element using the `/api/recording/files/{filename}` download endpoint as the source.

## Build

```bash
cd frontend
npm install
npm run build     # tsc + vite build → dist/
npm run dev       # Vite dev server on :5173 with HMR
```

The production build is a static `dist/` folder served by Nginx. The Nginx config handles SPA routing (all unknown paths return `index.html`) and proxies `/api/*` and `/hls/*` to the backend.

## Nginx Configuration (`nginx.conf`)

```nginx
location /api/ {
    proxy_pass http://backend:8000;
}

location /hls/ {
    proxy_pass http://backend:8000;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

`backend` resolves to the host gateway via the `extra_hosts` setting in `docker-compose.yml`.

## Styling

Tailwind CSS with a custom dark theme. CSS variables in `index.css` define:
- `--color-surface` — main background
- `--color-panel` — sidebar and card background
- `--color-border` — subtle borders

Radix UI headless components are styled with Tailwind utility classes for all interactive elements (dialogs, switches, tabs, selects, toasts).
