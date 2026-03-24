import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Upload, Search, BarChart3, Briefcase } from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload CV' },
  { to: '/recommend', icon: Search, label: 'Gợi ý việc làm' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-dark-800/90 backdrop-blur-xl border-r border-white/5 flex flex-col z-30">
      {/* Logo */}
      <div className="px-6 py-7 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/30">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-sm leading-tight">JobMatch AI</h1>
            <p className="text-slate-500 text-xs">SBERT Powered</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-link ${isActive ? 'active' : ''}`
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/5">
        <p className="text-slate-600 text-xs text-center">v2.0 — Continual Learning</p>
      </div>
    </aside>
  )
}
