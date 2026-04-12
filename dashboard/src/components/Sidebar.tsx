import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, CalendarDays, LogOut } from 'lucide-react'

const links = [
  { to: '/', label: '總覽', icon: LayoutDashboard },
  { to: '/users', label: '用戶', icon: Users },
  { to: '/schedules', label: '行程', icon: CalendarDays },
]

export default function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <aside className="w-56 bg-black text-white flex flex-col shrink-0">
      <div className="px-6 py-6 border-b border-gray-800">
        <p className="font-bold text-lg">Admin</p>
        <p className="text-gray-400 text-xs mt-1">Schedule Management</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition
              ${isActive ? 'bg-white text-black' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-800">
        <button
          onClick={onLogout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition"
        >
          <LogOut size={18} />
          登出
        </button>
      </div>
    </aside>
  )
}
