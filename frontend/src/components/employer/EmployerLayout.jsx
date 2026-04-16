import React from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Briefcase, Users, LogOut, ChevronRight, Sparkles
} from 'lucide-react'
import useAuthStore from '../../store/authStore'

const NAV = [
  { to: '/employer',           icon: LayoutDashboard, label: 'Dashboard',  end: true },
  { to: '/employer/company',   icon: Building2,        label: 'Công ty'              },
  { to: '/employer/jobs',      icon: Briefcase,        label: 'Tin tuyển dụng'       },
]

export default function EmployerLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-dark-900">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 flex flex-col bg-dark-800/80 border-r border-white/5 backdrop-blur-sm">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-600 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-600/30">
              <Sparkles size={15} className="text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-sm leading-none">JobMatch</p>
              <p className="text-brand-400 text-[10px] font-medium mt-0.5">Employer Portal</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={16} />
              {label}
              <ChevronRight size={12} className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="px-3 py-4 border-t border-white/5 space-y-1">
          <div className="px-4 py-3 rounded-xl bg-white/[0.03]">
            <p className="text-white text-sm font-medium truncate">{user?.full_name || user?.email || 'Employer'}</p>
            <p className="text-slate-500 text-xs mt-0.5 truncate">{user?.email}</p>
            <span className="badge-brand text-[10px] mt-1.5">Employer</span>
          </div>
          <button
            onClick={handleLogout}
            className="nav-link w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            <LogOut size={15} />
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="min-h-full p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
