import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Camera, Users, ClipboardList, Settings,
  Shield, Car, UserX, DoorOpen,
} from 'lucide-react'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/monitoring', icon: Camera, label: 'Live Monitor' },
  { to: '/students', icon: Users, label: 'Students' },
  { to: '/attendance', icon: ClipboardList, label: 'Attendance' },
  { to: '/gate', icon: DoorOpen, label: 'Gate Activity' },
  { to: '/visitors', icon: UserX, label: 'Visitors' },
  { to: '/vehicles', icon: Car, label: 'Vehicles' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-full w-56 bg-charcoal flex flex-col z-50 shadow-elevated">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-white/10">
        <div className="p-1.5 bg-forest rounded-lg">
          <Shield size={16} className="text-sage" />
        </div>
        <div>
          <span className="text-sm font-bold text-white tracking-wide">SmartGateAI</span>
          <p className="text-xs text-white/40 leading-none mt-0.5">Campus Security</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        <p className="px-3 pt-3 pb-1 text-xs font-semibold text-white/30 uppercase tracking-wider">
          Monitoring
        </p>
        {NAV.slice(0, 3).map(({ to, icon: Icon, label }) => (
          <NavItem key={to} to={to} icon={Icon} label={label} exact={to === '/'} />
        ))}
        <p className="px-3 pt-4 pb-1 text-xs font-semibold text-white/30 uppercase tracking-wider">
          Management
        </p>
        {NAV.slice(3).map(({ to, icon: Icon, label }) => (
          <NavItem key={to} to={to} icon={Icon} label={label} />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-white/10">
        <p className="text-xs text-white/30">v1.0 · Localhost Only</p>
      </div>
    </aside>
  )
}

function NavItem({ to, icon: Icon, label, exact }) {
  return (
    <NavLink
      to={to}
      end={exact}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-100 ${
          isActive
            ? 'bg-forest text-white shadow-sm'
            : 'text-white/60 hover:text-white hover:bg-white/8'
        }`
      }
    >
      <Icon size={16} className="flex-shrink-0" />
      {label}
    </NavLink>
  )
}
