import axios from 'axios'
import type { OnvifDevice, WebcamDevice, DvrChannel } from '../types'

export const startNetworkScan = () => axios.post<{ job_id: string }>('/api/scan/network').then(r => r.data)
export const getNetworkScan = (jobId: string) => axios.get(`/api/scan/network/${jobId}`).then(r => r.data)
export const onvifScan = () => axios.post<OnvifDevice[]>('/api/scan/onvif').then(r => r.data)
export const scanWebcams = () => axios.get<WebcamDevice[]>('/api/scan/webcams').then(r => r.data)
export const probeDvr = (ip: string, username: string, password: string, brand: string, channelCount: number) =>
  axios.post<{ ip: string; brand: string; channels: DvrChannel[] }>('/api/scan/dvr', {
    ip, username, password, brand, channel_count: channelCount,
  }).then(r => r.data)
export const addAllDvrChannels = (channels: DvrChannel[], dvrHost: string, brand: string, username: string, password: string) =>
  axios.post('/api/scan/dvr/add-all', { channels, dvr_host: dvrHost, brand, username, password }).then(r => r.data)
export const probeIp = (ip: string, port: number, username: string, password: string) =>
  axios.post('/api/scan/probe', { ip, port, username, password }).then(r => r.data)
