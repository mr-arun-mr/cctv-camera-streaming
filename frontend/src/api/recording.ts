import axios from 'axios'
import type { RecordingStatus, RecordingFile } from '../types'

export const startRecording = (id: number) => axios.post(`/api/recording/${id}/start`).then(r => r.data)
export const stopRecording = (id: number) => axios.post(`/api/recording/${id}/stop`).then(r => r.data)
export const getRecordingStatus = (id: number) => axios.get<RecordingStatus>(`/api/recording/${id}/status`).then(r => r.data)
export const listRecordings = () => axios.get<RecordingFile[]>('/api/recording/files').then(r => r.data)
export const deleteRecording = (filename: string) => axios.delete(`/api/recording/files/${encodeURIComponent(filename)}`)
