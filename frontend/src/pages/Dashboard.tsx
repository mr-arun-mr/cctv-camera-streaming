import { useQuery } from '@tanstack/react-query'
import { getCameras } from '../api/cameras'
import CameraGrid from '../components/CameraGrid'

export default function Dashboard() {
  const { data: cameras = [], isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: getCameras,
    refetchInterval: 15000,
  })

  const active = cameras.filter((c) => c.enabled)

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border">
        <h1 className="text-base font-semibold">Live Dashboard</h1>
      </div>
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">Loading…</div>
      ) : (
        <div className="flex-1 min-h-0">
          <CameraGrid cameras={active} />
        </div>
      )}
    </div>
  )
}
