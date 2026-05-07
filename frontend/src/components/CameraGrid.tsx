import { useState } from 'react'
import { Grid2X2, Grid3X3, LayoutGrid } from 'lucide-react'
import CameraCard from './CameraCard'
import type { Camera } from '../types'

interface Props {
  cameras: Camera[]
}

const layouts = [
  { cols: 1, label: '1×1', icon: LayoutGrid },
  { cols: 2, label: '2×2', icon: Grid2X2 },
  { cols: 3, label: '3×3', icon: Grid3X3 },
  { cols: 4, label: '4×4', icon: LayoutGrid },
]

export default function CameraGrid({ cameras }: Props) {
  const [cols, setCols] = useState(2)
  const visible = cameras.slice(0, cols * cols)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border">
        <span className="text-xs text-gray-400 mr-2">Layout</span>
        {layouts.map((l) => (
          <button
            key={l.cols}
            onClick={() => setCols(l.cols)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              cols === l.cols
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {l.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-500">
          {cameras.length} camera{cameras.length !== 1 ? 's' : ''}
        </span>
      </div>

      {cameras.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
          No cameras added yet. Go to <strong className="mx-1 text-blue-400">Cameras</strong> to add one.
        </div>
      ) : (
        <div
          className="flex-1 p-3 grid gap-2"
          style={{
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gridTemplateRows: `repeat(${cols}, 1fr)`,
          }}
        >
          {visible.map((cam) => (
            <CameraCard key={cam.id} camera={cam} />
          ))}
        </div>
      )}
    </div>
  )
}
