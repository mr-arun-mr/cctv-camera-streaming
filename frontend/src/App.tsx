import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Video, Camera, Search, Film } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Cameras from './pages/Cameras'
import Discover from './pages/Discover'
import Recordings from './pages/Recordings'

const navItems = [
  { to: '/', label: 'Dashboard', icon: Video },
  { to: '/cameras', label: 'Cameras', icon: Camera },
  { to: '/discover', label: 'Discover', icon: Search },
  { to: '/recordings', label: 'Recordings', icon: Film },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <nav className="w-56 bg-panel border-r border-border flex flex-col shrink-0">
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Video className="text-blue-400" size={22} />
              <span className="font-semibold text-sm">CCTV Stream</span>
            </div>
          </div>
          <ul className="p-2 flex flex-col gap-1 mt-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    }`
                  }
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main className="flex-1 overflow-auto bg-surface">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/discover" element={<Discover />} />
            <Route path="/recordings" element={<Recordings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
