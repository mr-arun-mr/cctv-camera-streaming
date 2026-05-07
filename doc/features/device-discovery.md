# Device Discovery

The Discover page provides four methods to find cameras on the network and add them to the system. Each method targets a different type of device.

## 1. Network Scan

**Endpoint:** `POST /api/scan/network` → `GET /api/scan/network/{job_id}`

Scans the local subnet for hosts with camera-related ports open.

### How it works

1. Detects the local subnet from `psutil.net_if_addrs()` — uses the first non-loopback IPv4 interface and constructs a `/24` subnet (e.g. `192.168.1.0/24`)
2. Generates all 254 host IPs (`.1` through `.254`)
3. Probes TCP ports 554 (RTSP), 8554 (RTSP alt), 8080 (HTTP cam), 80 (HTTP) concurrently in batches of 50
4. For hosts with at least one open port, performs a reverse DNS lookup
5. Returns a list of discovered hosts with open ports and hostname

### Response structure

```json
{
  "status": "done",
  "results": [
    {
      "ip": "192.168.1.100",
      "open_ports": [554, 80],
      "hostname": "camera1.local",
      "mac": ""
    }
  ]
}
```

The scan is async and starts immediately; poll the job ID endpoint until `"status": "done"`. The job result is stored in memory until the next scan.

### Limitations

- Only scans the /24 subnet of the first non-loopback interface
- MAC address is always empty (ARP lookup not implemented)
- TCP connection is opened and closed without sending data; some devices may reject the connection even if the port is open

### After discovery

Use `POST /api/scan/probe` to test specific RTSP URL patterns for a discovered IP before adding it as a camera.

---

## 2. ONVIF Discovery

**Endpoint:** `POST /api/scan/onvif`

Uses ONVIF WS-Discovery (Web Services Discovery) to find ONVIF-compatible cameras via UDP multicast.

### How it works

1. Creates a `ThreadedWSDiscovery` instance from the `wsdiscovery` library
2. Sends a WS-Discovery `Probe` on UDP multicast address `239.255.255.250:3702`
3. Waits 5 seconds for `Hello` responses
4. Filters responses that contain `onvif` in their scopes
5. Extracts IP address from `XAddrs`, and manufacturer/model from ONVIF scope URIs:
   - `onvif://www.onvif.org/name/<manufacturer>`
   - `onvif://www.onvif.org/hardware/<model>`

### Response structure

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

`rtsp_url` is empty in discovery results. To retrieve the RTSP URL, the frontend calls `POST /api/scan/probe` or the ONVIF service can be queried directly with credentials.

### Fetching RTSP via ONVIF

`onvif_scanner.get_rtsp_url(ip, port, username, password)` uses `onvif-zeep` to:
1. Connect to the ONVIF device service
2. Call `GetProfiles` to list media profiles
3. Call `GetStreamUri` with `RTP-Unicast / RTSP` for the first profile
4. Return the RTSP URI

### Requirements

ONVIF WS-Discovery requires UDP multicast to work, which is why the backend uses `network_mode: host`. Without host networking, multicast packets cannot leave the Docker bridge network.

---

## 3. Webcam / Capture Card Scanner

**Endpoint:** `GET /api/scan/webcams`

Enumerates locally connected USB webcams and video capture cards.

### How it works

1. Iterates device indices 0–9 using `cv2.VideoCapture(index)`
2. Skips devices that cannot be opened or fail to read a frame
3. Reads `CAP_PROP_FRAME_WIDTH` and `CAP_PROP_FRAME_HEIGHT`
4. Uses `v4l2-ctl --info` to read the card name
5. Uses `v4l2-ctl --list-inputs` to check for composite/HDMI/S-Video inputs (identifies capture cards)

### Response structure

```json
[
  {
    "device_index": 0,
    "device_path": "/dev/video0",
    "width": 1920,
    "height": 1080,
    "name": "USB 2.0 Camera",
    "is_capture_card": false
  },
  {
    "device_index": 1,
    "device_path": "/dev/video1",
    "width": 720,
    "height": 576,
    "name": "AV Capture Card",
    "is_capture_card": true
  }
]
```

### Requirements

Devices must be passed through to the container via the `devices` section of `docker-compose.yml`. See [Deployment](../deployment.md).

---

## 4. DVR Channel Probing

**Endpoints:** `POST /api/scan/dvr` and `POST /api/scan/dvr/add-all`

Probes a DVR or NVR for active RTSP channels using brand-specific URL patterns.

### How it works

1. Takes DVR IP, credentials, brand, and channel count
2. For each channel number (1 to `channel_count`), builds candidate RTSP URLs based on the brand pattern
3. Tests each URL with `ffprobe -v quiet -i <url>` (6-second timeout)
4. Returns channels where ffprobe returns exit code 0

### Brand URL Patterns

| Brand | RTSP URL pattern |
|---|---|
| `hikvision` | `rtsp://{user}:{pwd}@{ip}:554/Streaming/Channels/{ch:02d}01` |
| `dahua` | `rtsp://{user}:{pwd}@{ip}:554/cam/realmonitor?channel={ch}&subtype=0` |
| `uniview` | `rtsp://{user}:{pwd}@{ip}:554/unicast/c{ch}/s0/live` |
| `generic` | Multiple patterns tried: `/ch{ch:02d}`, `/channel{ch}`, `/h264/ch{ch}/main/av_stream`, `/cam/realmonitor?channel={ch}&subtype=0` |

### Request

```json
{
  "ip": "192.168.1.200",
  "username": "admin",
  "password": "admin",
  "brand": "hikvision",
  "channel_count": 16
}
```

All 16 channels are probed concurrently via `asyncio.gather`.

### Response

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

### Bulk Add

After probing, use `POST /api/scan/dvr/add-all` to bulk-create Camera records for all discovered channels:

```json
{
  "channels": [ ... ],
  "dvr_host": "192.168.1.200",
  "brand": "hikvision",
  "username": "admin",
  "password": "admin"
}
```

Each created camera has `camera_type="dvr_channel"` and stores `dvr_host`, `channel_number`, and `dvr_brand`.

---

## IP Probe

**Endpoint:** `POST /api/scan/probe`

Tests a specific IP address by trying common RTSP URL paths with ffprobe.

```json
{ "ip": "192.168.1.100", "port": 554, "username": "admin", "password": "pass" }
```

Tries these paths in order (with credentials if provided):
- `rtsp://user:pass@ip:port/`
- `rtsp://user:pass@ip:port/stream`
- `rtsp://user:pass@ip:port/live`

Returns the first URL that succeeds, or `{ "rtsp_url": null, "reachable": false }`.
