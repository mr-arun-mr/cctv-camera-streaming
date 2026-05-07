import { create } from 'zustand'
import type { Camera, StreamStatus, RecordingStatus } from '../types'

interface CameraStore {
  cameras: Camera[]
  streamStatuses: Record<number, StreamStatus>
  recordingStatuses: Record<number, RecordingStatus>
  setCameras: (cameras: Camera[]) => void
  setStreamStatus: (id: number, status: StreamStatus) => void
  setRecordingStatus: (id: number, status: RecordingStatus) => void
}

export const useCameraStore = create<CameraStore>((set) => ({
  cameras: [],
  streamStatuses: {},
  recordingStatuses: {},
  setCameras: (cameras) => set({ cameras }),
  setStreamStatus: (id, status) =>
    set((s) => ({ streamStatuses: { ...s.streamStatuses, [id]: status } })),
  setRecordingStatus: (id, status) =>
    set((s) => ({ recordingStatuses: { ...s.recordingStatuses, [id]: status } })),
}))
