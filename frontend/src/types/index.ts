export interface Camera {
  id: number
  name: string
  ip_address: string | null
  rtsp_url: string | null
  device_index: number | null
  device_path: string | null
  username: string | null
  password: string | null
  camera_type: 'onvif' | 'ip' | 'rtsp' | 'webcam' | 'usb_capture' | 'dvr_channel'
  dvr_host: string | null
  channel_number: number | null
  dvr_brand: string | null
  enabled: boolean
  motion_detection: boolean
  motion_threshold: number
  continuous_recording: boolean
  created_at: string
}

export interface StreamStatus {
  active: boolean
  started_at: string | null
  segment_count: number
}

export interface RecordingStatus {
  recording: boolean
  recording_type: string | null
  started_at: string | null
  file_path: string | null
}

export interface RecordingFile {
  filename: string
  camera_id: number | null
  size_bytes: number
  created_at: string
  recording_type: string | null
}

export interface Schedule {
  id: number
  camera_id: number
  days_of_week: string
  start_time: string
  end_time: string
  enabled: boolean
}

export interface ScanHost {
  ip: string
  open_ports: number[]
  hostname: string
  mac: string
}

export interface OnvifDevice {
  ip: string
  xaddr: string
  manufacturer: string
  model: string
  rtsp_url: string
}

export interface WebcamDevice {
  device_index: number
  device_path: string
  width: number
  height: number
  name: string
  is_capture_card: boolean
}

export interface DvrChannel {
  channel: number
  rtsp_url: string
  name: string
}
