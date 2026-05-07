import { useState, useEffect } from 'react'
import { Circle, StopCircle, Zap } from 'lucide-react'
import VideoPlayer from './VideoPlayer'
import { startStream, stopStream, getStreamStatus } from '../api/stream'
import { startRecording, stopRecording, getRecordingStatus } from '../api/recording'
import type { Camera } from '../types'

interface Props {
  camera: Camera
}

export default function CameraCard({ camera }: Props) {
  const [streamActive, setStreamActive] = useState(false)
  const [recording, setRecording] = useState(false)
  const [motion, setMotion] = useState(false)

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const [ss, rs] = await Promise.all([
          getStreamStatus(camera.id),
          getRecordingStatus(camera.id),
        ])
        if (!cancelled) {
          setStreamActive(ss.active)
          setRecording(rs.recording)
        }
      } catch {}
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [camera.id])

  useEffect(() => {
    startStream(camera.id).catch(() => {})
    return () => { stopStream(camera.id).catch(() => {}) }
  }, [camera.id])

  const toggleRecord = async () => {
    if (recording) {
      await stopRecording(camera.id)
      setRecording(false)
    } else {
      await startRecording(camera.id)
      setRecording(true)
    }
  }

  const typeLabel: Record<string, string> = {
    onvif: 'ONVIF', ip: 'IP', rtsp: 'RTSP',
    webcam: 'Webcam', usb_capture: 'Capture', dvr_channel: 'DVR',
  }

  return (
    <div className="relative flex flex-col bg-black rounded-lg overflow-hidden border border-border">
      <div className="flex-1 min-h-0">
        <VideoPlayer cameraId={camera.id} active={streamActive} />
      </div>

      {/* Overlay bar */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-medium truncate text-white">{camera.name}</span>
          <span className="text-[10px] bg-gray-700 text-gray-300 px-1 rounded shrink-0">
            {typeLabel[camera.camera_type] ?? camera.camera_type}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {camera.motion_detection && (
            <Zap
              size={13}
              className={motion ? 'text-yellow-400' : 'text-gray-600'}
              title="Motion detection"
            />
          )}
          <button onClick={toggleRecord} title={recording ? 'Stop recording' : 'Start recording'}>
            {recording ? (
              <StopCircle size={16} className="text-red-500 animate-pulse" />
            ) : (
              <Circle size={16} className="text-gray-400 hover:text-red-400" />
            )}
          </button>
        </div>
      </div>

      {recording && (
        <div className="absolute top-2 right-2 flex items-center gap-1 bg-red-600/90 text-white text-[10px] px-1.5 py-0.5 rounded">
          <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
          REC
        </div>
      )}
    </div>
  )
}
