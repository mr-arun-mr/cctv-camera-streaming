import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Wifi, Monitor, HardDrive, Plus, Loader2 } from 'lucide-react'
import { startNetworkScan, getNetworkScan, onvifScan, scanWebcams, probeDvr, addAllDvrChannels } from '../api/scanner'
import { createCamera } from '../api/cameras'
import type { ScanHost, OnvifDevice, WebcamDevice, DvrChannel } from '../types'

export default function Discover() {
  const qc = useQueryClient()

  // Network scan
  const [netStatus, setNetStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [netHosts, setNetHosts] = useState<ScanHost[]>([])

  // ONVIF
  const [onvifStatus, setOnvifStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [onvifDevices, setOnvifDevices] = useState<OnvifDevice[]>([])

  // Webcams
  const [webcamStatus, setWebcamStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [webcams, setWebcams] = useState<WebcamDevice[]>([])

  // DVR
  const [dvrForm, setDvrForm] = useState({ ip: '', username: 'admin', password: '', brand: 'generic', channelCount: 16 })
  const [dvrStatus, setDvrStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [dvrChannels, setDvrChannels] = useState<DvrChannel[]>([])

  const addMut = useMutation({
    mutationFn: createCamera,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cameras'] }),
  })

  const handleNetworkScan = async () => {
    setNetStatus('running')
    setNetHosts([])
    try {
      const { job_id } = await startNetworkScan()
      const poll = setInterval(async () => {
        const res = await getNetworkScan(job_id)
        if (res.status === 'done') {
          clearInterval(poll)
          setNetHosts(res.results)
          setNetStatus('done')
        }
      }, 2000)
    } catch { setNetStatus('idle') }
  }

  const handleOnvifScan = async () => {
    setOnvifStatus('running')
    setOnvifDevices([])
    try {
      const devices = await onvifScan()
      setOnvifDevices(devices)
      setOnvifStatus('done')
    } catch { setOnvifStatus('idle') }
  }

  const handleWebcamScan = async () => {
    setWebcamStatus('running')
    setWebcams([])
    try {
      const devices = await scanWebcams()
      setWebcams(devices)
      setWebcamStatus('done')
    } catch { setWebcamStatus('idle') }
  }

  const handleDvrProbe = async () => {
    setDvrStatus('running')
    setDvrChannels([])
    try {
      const res = await probeDvr(dvrForm.ip, dvrForm.username, dvrForm.password, dvrForm.brand, dvrForm.channelCount)
      setDvrChannels(res.channels)
      setDvrStatus('done')
    } catch { setDvrStatus('idle') }
  }

  const handleAddAllDvr = async () => {
    await addAllDvrChannels(dvrChannels, dvrForm.ip, dvrForm.brand, dvrForm.username, dvrForm.password)
    qc.invalidateQueries({ queryKey: ['cameras'] })
  }

  return (
    <div className="p-4 space-y-6 max-w-3xl">
      <h1 className="text-base font-semibold">Discover Cameras</h1>

      {/* Network Scan */}
      <section className="bg-panel border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wifi size={16} className="text-blue-400" />
            <h2 className="text-sm font-medium">Network Scan</h2>
          </div>
          <button className="btn-primary text-sm flex items-center gap-1.5" onClick={handleNetworkScan} disabled={netStatus === 'running'}>
            {netStatus === 'running' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {netStatus === 'running' ? 'Scanning…' : 'Scan LAN'}
          </button>
        </div>
        {netHosts.length > 0 && (
          <div className="space-y-1.5">
            {netHosts.map((h) => (
              <div key={h.ip} className="flex items-center justify-between bg-surface rounded px-3 py-2">
                <div>
                  <span className="text-sm font-mono">{h.ip}</span>
                  {h.hostname && <span className="text-xs text-gray-400 ml-2">{h.hostname}</span>}
                  <div className="text-xs text-gray-500">Ports: {h.open_ports.join(', ')}</div>
                </div>
                <button className="btn-ghost text-xs flex items-center gap-1"
                  onClick={() => addMut.mutate({ name: h.hostname || h.ip, ip_address: h.ip, rtsp_url: `rtsp://${h.ip}:554/`, camera_type: 'ip' })}>
                  <Plus size={12} /> Add
                </button>
              </div>
            ))}
          </div>
        )}
        {netStatus === 'done' && netHosts.length === 0 && (
          <p className="text-xs text-gray-500">No hosts with open RTSP ports found.</p>
        )}
      </section>

      {/* ONVIF Scan */}
      <section className="bg-panel border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search size={16} className="text-green-400" />
            <h2 className="text-sm font-medium">ONVIF Discovery</h2>
          </div>
          <button className="btn-primary text-sm flex items-center gap-1.5" onClick={handleOnvifScan} disabled={onvifStatus === 'running'}>
            {onvifStatus === 'running' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {onvifStatus === 'running' ? 'Discovering…' : 'Discover ONVIF'}
          </button>
        </div>
        {onvifDevices.length > 0 && (
          <div className="space-y-1.5">
            {onvifDevices.map((d, i) => (
              <div key={i} className="flex items-center justify-between bg-surface rounded px-3 py-2">
                <div>
                  <span className="text-sm font-mono">{d.ip}</span>
                  <span className="text-xs text-gray-400 ml-2">{d.manufacturer} {d.model}</span>
                  <div className="text-xs text-gray-500 font-mono">{d.rtsp_url || d.xaddr}</div>
                </div>
                <button className="btn-ghost text-xs flex items-center gap-1"
                  onClick={() => addMut.mutate({ name: d.model || d.ip, ip_address: d.ip, rtsp_url: d.rtsp_url, camera_type: 'onvif' })}>
                  <Plus size={12} /> Add
                </button>
              </div>
            ))}
          </div>
        )}
        {onvifStatus === 'done' && onvifDevices.length === 0 && (
          <p className="text-xs text-gray-500">No ONVIF devices found on the network.</p>
        )}
      </section>

      {/* DVR/NVR */}
      <section className="bg-panel border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2">
          <HardDrive size={16} className="text-orange-400" />
          <h2 className="text-sm font-medium">DVR / NVR (Analog cameras)</h2>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-400 block mb-1">DVR IP</label>
            <input className="input w-full" value={dvrForm.ip} onChange={(e) => setDvrForm((f) => ({ ...f, ip: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Brand</label>
            <select className="input w-full" value={dvrForm.brand} onChange={(e) => setDvrForm((f) => ({ ...f, brand: e.target.value }))}>
              <option value="generic">Generic</option>
              <option value="hikvision">Hikvision</option>
              <option value="dahua">Dahua</option>
              <option value="uniview">Uniview</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Username</label>
            <input className="input w-full" value={dvrForm.username} onChange={(e) => setDvrForm((f) => ({ ...f, username: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Password</label>
            <input className="input w-full" type="password" value={dvrForm.password} onChange={(e) => setDvrForm((f) => ({ ...f, password: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Channels to probe</label>
            <input className="input w-full" type="number" min={1} max={64} value={dvrForm.channelCount} onChange={(e) => setDvrForm((f) => ({ ...f, channelCount: Number(e.target.value) }))} />
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary text-sm flex items-center gap-1.5" onClick={handleDvrProbe} disabled={!dvrForm.ip || dvrStatus === 'running'}>
            {dvrStatus === 'running' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {dvrStatus === 'running' ? 'Probing…' : 'Probe DVR'}
          </button>
          {dvrChannels.length > 0 && (
            <button className="btn-ghost text-sm flex items-center gap-1.5" onClick={handleAddAllDvr}>
              <Plus size={14} /> Add All ({dvrChannels.length})
            </button>
          )}
        </div>
        {dvrChannels.length > 0 && (
          <div className="space-y-1">
            {dvrChannels.map((ch) => (
              <div key={ch.channel} className="flex items-center justify-between bg-surface rounded px-3 py-1.5">
                <div>
                  <span className="text-sm">{ch.name}</span>
                  <span className="text-xs text-gray-500 ml-2 font-mono">{ch.rtsp_url}</span>
                </div>
                <button className="btn-ghost text-xs flex items-center gap-1"
                  onClick={() => addMut.mutate({ name: ch.name, ip_address: dvrForm.ip, rtsp_url: ch.rtsp_url, camera_type: 'dvr_channel', dvr_host: dvrForm.ip, channel_number: ch.channel, dvr_brand: dvrForm.brand })}>
                  <Plus size={12} /> Add
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Local Devices */}
      <section className="bg-panel border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor size={16} className="text-purple-400" />
            <h2 className="text-sm font-medium">Local Devices (Webcam / USB Capture Card)</h2>
          </div>
          <button className="btn-primary text-sm flex items-center gap-1.5" onClick={handleWebcamScan} disabled={webcamStatus === 'running'}>
            {webcamStatus === 'running' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {webcamStatus === 'running' ? 'Scanning…' : 'Scan Devices'}
          </button>
        </div>
        {webcams.length > 0 && (
          <div className="space-y-1.5">
            {webcams.map((w) => (
              <div key={w.device_index} className="flex items-center justify-between bg-surface rounded px-3 py-2">
                <div>
                  <span className="text-sm">{w.name}</span>
                  <span className="text-xs text-gray-400 ml-2">{w.device_path}</span>
                  <div className="flex gap-2 mt-0.5">
                    <span className="text-xs text-gray-500">{w.width}×{w.height}</span>
                    {w.is_capture_card && <span className="text-[10px] bg-orange-900/40 text-orange-400 px-1.5 rounded">Capture Card (Analog)</span>}
                  </div>
                </div>
                <button className="btn-ghost text-xs flex items-center gap-1"
                  onClick={() => addMut.mutate({ name: w.name, device_index: w.device_index, device_path: w.device_path, camera_type: w.is_capture_card ? 'usb_capture' : 'webcam' })}>
                  <Plus size={12} /> Add
                </button>
              </div>
            ))}
          </div>
        )}
        {webcamStatus === 'done' && webcams.length === 0 && (
          <p className="text-xs text-gray-500">No local video devices found.</p>
        )}
      </section>
    </div>
  )
}
