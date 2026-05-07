import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, Download, Film } from 'lucide-react'
import { listRecordings, deleteRecording } from '../api/recording'

const TYPES: Record<string, { label: string; color: string }> = {
  manual: { label: 'Manual', color: 'text-blue-400' },
  continuous: { label: 'Continuous', color: 'text-green-400' },
  scheduled: { label: 'Scheduled', color: 'text-purple-400' },
  motion: { label: 'Motion', color: 'text-yellow-400' },
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

export default function Recordings() {
  const qc = useQueryClient()
  const { data: recordings = [], isLoading } = useQuery({
    queryKey: ['recordings'],
    queryFn: listRecordings,
    refetchInterval: 10000,
  })

  const deleteMut = useMutation({
    mutationFn: deleteRecording,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recordings'] }),
  })

  const totalSize = recordings.reduce((s, r) => s + r.size_bytes, 0)

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold">Recordings</h1>
        <span className="text-xs text-gray-400">
          {recordings.length} file{recordings.length !== 1 ? 's' : ''} · {formatBytes(totalSize)} total
        </span>
      </div>

      {isLoading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : recordings.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <Film size={40} className="mb-3 opacity-30" />
          <p className="text-sm">No recordings yet.</p>
          <p className="text-xs mt-1">Start recording from the Dashboard or enable continuous/motion recording on a camera.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {recordings.map((rec) => {
            const typeInfo = TYPES[rec.recording_type ?? ''] ?? { label: rec.recording_type ?? '?', color: 'text-gray-400' }
            return (
              <div key={rec.filename} className="bg-panel border border-border rounded-lg px-4 py-3 flex items-center gap-3">
                <Film size={18} className="text-gray-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono truncate">{rec.filename}</div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className={`text-xs ${typeInfo.color}`}>{typeInfo.label}</span>
                    <span className="text-xs text-gray-500">{formatBytes(rec.size_bytes)}</span>
                    <span className="text-xs text-gray-500">{formatDate(rec.created_at)}</span>
                    {rec.camera_id && <span className="text-xs text-gray-600">Camera #{rec.camera_id}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <a
                    href={`/api/recording/files/${encodeURIComponent(rec.filename)}`}
                    download={rec.filename}
                    className="btn-ghost flex items-center gap-1 text-xs"
                  >
                    <Download size={13} /> Download
                  </a>
                  <button
                    className="btn-ghost text-red-400"
                    onClick={() => deleteMut.mutate(rec.filename)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
