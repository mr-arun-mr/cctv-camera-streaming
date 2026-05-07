import axios from 'axios'
import type { StreamStatus } from '../types'

export const startStream = (id: number) => axios.post(`/api/stream/${id}/start`).then(r => r.data)
export const stopStream = (id: number) => axios.post(`/api/stream/${id}/stop`).then(r => r.data)
export const getStreamStatus = (id: number) => axios.get<StreamStatus>(`/api/stream/${id}/status`).then(r => r.data)
