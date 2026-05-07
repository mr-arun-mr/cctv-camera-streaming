import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'
import { Loader2, WifiOff } from 'lucide-react'

interface Props {
  cameraId: number
  active: boolean
}

export default function VideoPlayer({ cameraId, active }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const [state, setState] = useState<'loading' | 'playing' | 'error'>('loading')

  useEffect(() => {
    if (!active || !videoRef.current) {
      setState('loading')
      return
    }

    const src = `/hls/${cameraId}/stream.m3u8`

    const setup = () => {
      if (Hls.isSupported()) {
        const hls = new Hls({
          lowLatencyMode: true,
          backBufferLength: 10,
        })
        hlsRef.current = hls
        hls.loadSource(src)
        hls.attachMedia(videoRef.current!)
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          videoRef.current?.play().catch(() => {})
          setState('playing')
        })
        hls.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) {
            setState('error')
            setTimeout(() => {
              hls.destroy()
              setup()
            }, 3000)
          }
        })
      } else if (videoRef.current!.canPlayType('application/vnd.apple.mpegurl')) {
        videoRef.current!.src = src
        videoRef.current!.play().catch(() => {})
        setState('playing')
      }
    }

    setup()

    return () => {
      hlsRef.current?.destroy()
      hlsRef.current = null
    }
  }, [cameraId, active])

  return (
    <div className="relative w-full h-full bg-black">
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        muted
        playsInline
      />
      {state === 'loading' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <Loader2 className="animate-spin text-blue-400" size={32} />
        </div>
      )}
      {state === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 gap-2">
          <WifiOff className="text-red-400" size={28} />
          <span className="text-xs text-red-300">Stream unavailable — retrying…</span>
        </div>
      )}
    </div>
  )
}
