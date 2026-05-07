import axios from 'axios'
import type { Camera } from '../types'

const base = '/api/cameras'

export const getCameras = () => axios.get<Camera[]>(base).then(r => r.data)
export const getCamera = (id: number) => axios.get<Camera>(`${base}/${id}`).then(r => r.data)
export const createCamera = (data: Partial<Camera>) => axios.post<Camera>(base, data).then(r => r.data)
export const updateCamera = (id: number, data: Partial<Camera>) => axios.put<Camera>(`${base}/${id}`, data).then(r => r.data)
export const deleteCamera = (id: number) => axios.delete(`${base}/${id}`)
export const testCamera = (id: number) => axios.post(`${base}/${id}/test`).then(r => r.data)
