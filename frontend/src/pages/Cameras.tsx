import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, CheckCircle, XCircle, Loader2, Edit2 } from 'lucide-react'
import { getCameras, createCamera, updateCamera, deleteCamera, testCamera } from '../api/cameras'
import type { Camera } from '../types'

const EMPTY: Partial<Camera> = {
  name: '', ip_address: '', rtsp_url: '', camera_type: 'ip',
  username: '', password: '', enabled: true,
  motion_detection: false, continuous_recording: false, motion_threshold: 500,
}

function CameraForm({ initial, onSave, onCancel }: {
  initial: Partial<Camera>
  onSave: (data: Partial<Camera>) => void
  onCancel: () => void
}) {
  const [form, setForm] = useState(initial)
  const set = (k: keyof Camera, v: unknown) => setForm((f) => ({ ...f, [k]: v }))
  const isLocal = form.camera_type === 'webcam' || form.camera_type === 'usb_capture'

  return (
    <div className="bg-panel border border-border rounded-lg p-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Name *</label>
          <input className="input w-full" value={form.name ?? ''} onChange={(e) => set('name', e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Type</label>
          <select className="input w-full" value={form.camera_type ?? 'ip'} onChange={(e) => set('camera_type', e.target.value)}>
            <option value="ip">IP Camera</option>
            <option value="onvif">ONVIF</option>
            <option value="rtsp">RTSP</option>
            <option value="dvr_channel">DVR Channel</option>
            <option value="webcam">Webcam (USB)</option>
            <option value="usb_capture">USB Capture Card</option>
          </select>
        </div>
      </div>

      {!isLocal && (
        <>
          <div>
            <label className="text-xs text-gray-400 block mb-1">IP Address</label>
            <input className="input w-full" value={form.ip_address ?? ''} onChange={(e) => set('ip_address', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">RTSP URL</label>
            <input className="input w-full font-mono text-xs" placeholder="rtsp://…" value={form.rtsp_url ?? ''} onChange={(e) => set('rtsp_url', e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Username</label>
              <input className="input w-full" value={form.username ?? ''} onChange={(e) => set('username', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Password</label>
              <input className="input w-full" type="password" value={form.password ?? ''} onChange={(e) => set('password', e.target.value)} />
            </div>
          </div>
        </>
      )}

      {isLocal && (
        <div>
          <label className="text-xs text-gray-400 block mb-1">Device Index</label>
          <input className="input w-full" type="number" min={0} value={form.device_index ?? 0} onChange={(e) => set('device_index', Number(e.target.value))} />
        </div>
      )}

      <div className="flex items-center gap-6 pt-1">
        {(['enabled', 'motion_detection', 'continuous_recording'] as const).map((field) => (
          <label key={field} className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
            <input type="checkbox" checked={!!form[field]} onChange={(e) => set(field, e.target.checked)} className="rounded" />
            {field.replace(/_/g, ' ')}
          </label>
        ))}
      </div>

      <div className="flex gap-2 pt-1">
        <button className="btn-primary text-sm" onClick={() => onSave(form)}>Save</button>
        <button className="btn-ghost text-sm" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

export default function Cameras() {
  const qc = useQueryClient()
  const { data: cameras = [], isLoading } = useQuery({ queryKey: ['cameras'], queryFn: getCameras })
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState<Camera | null>(null)
  const [testResults, setTestResults] = useState<Record<number, { ok: boolean; msg: string }>>({})

  const createMut = useMutation({
    mutationFn: createCamera,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cameras'] }); setShowAdd(false) },
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Camera> }) => updateCamera(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cameras'] }); setEditing(null) },
  })
  const deleteMut = useMutation({
    mutationFn: deleteCamera,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cameras'] }),
  })

  const handleTest = async (id: number) => {
    setTestResults((r) => ({ ...r, [id]: { ok: false, msg: '…' } }))
    const res = await testCamera(id)
    setTestResults((r) => ({
      ...r,
      [id]: { ok: res.ok, msg: res.ok ? `OK (${res.latency_ms}ms)` : res.error ?? 'Failed' },
    }))
  }

  const typeLabel: Record<string, string> = {
    onvif: 'ONVIF', ip: 'IP', rtsp: 'RTSP',
    webcam: 'Webcam', usb_capture: 'USB Capture', dvr_channel: 'DVR',
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold">Cameras</h1>
        <button className="btn-primary flex items-center gap-1.5 text-sm" onClick={() => setShowAdd(true)}>
          <Plus size={15} /> Add Camera
        </button>
      </div>

      {showAdd && (
        <CameraForm
          initial={EMPTY}
          onSave={(data) => createMut.mutate(data)}
          onCancel={() => setShowAdd(false)}
        />
      )}

      {isLoading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : cameras.length === 0 ? (
        <div className="text-gray-500 text-sm">No cameras yet. Add one above or use Discover.</div>
      ) : (
        <div className="space-y-2">
          {cameras.map((cam) =>
            editing?.id === cam.id ? (
              <CameraForm
                key={cam.id}
                initial={cam}
                onSave={(data) => updateMut.mutate({ id: cam.id, data })}
                onCancel={() => setEditing(null)}
              />
            ) : (
              <div key={cam.id} className="bg-panel border border-border rounded-lg px-4 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">{cam.name}</span>
                    <span className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">
                      {typeLabel[cam.camera_type] ?? cam.camera_type}
                    </span>
                    {!cam.enabled && <span className="text-[10px] bg-yellow-900/50 text-yellow-400 px-1.5 py-0.5 rounded">Disabled</span>}
                    {cam.continuous_recording && <span className="text-[10px] bg-red-900/40 text-red-400 px-1.5 py-0.5 rounded">REC</span>}
                    {cam.motion_detection && <span className="text-[10px] bg-blue-900/40 text-blue-400 px-1.5 py-0.5 rounded">Motion</span>}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 truncate font-mono">
                    {cam.rtsp_url || cam.device_path || cam.ip_address || '—'}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {testResults[cam.id] && (
                    <span className={`text-xs flex items-center gap-1 ${testResults[cam.id].ok ? 'text-green-400' : 'text-red-400'}`}>
                      {testResults[cam.id].ok ? <CheckCircle size={12} /> : <XCircle size={12} />}
                      {testResults[cam.id].msg}
                    </span>
                  )}
                  <button className="btn-ghost text-xs" onClick={() => handleTest(cam.id)}>Test</button>
                  <button className="btn-ghost" onClick={() => setEditing(cam)}><Edit2 size={14} /></button>
                  <button className="btn-ghost text-red-400" onClick={() => deleteMut.mutate(cam.id)}><Trash2 size={14} /></button>
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}
