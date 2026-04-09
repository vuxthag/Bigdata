import React, { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Briefcase, Menu, X, LogIn, UserPlus, ChevronDown } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import Footer from '../Footer'

const publicNavItems = [
  { to: '/', label: 'Trang chủ' },
  { to: '/jobs', label: 'Việc làm' },
  { to: '/companies', label: 'Công ty' },
  { to: '/recommend', label: 'AI Gợi ý' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function PublicLayout({ hideFooter = false }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { isAuthenticated, user, logout } = useAuthStore()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col bg-dark-900">
      {/* ── Navbar ─────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-dark-900/80 backdrop-blur-xl border-b border-white/5">
        <div className="section-container">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/30 group-hover:shadow-brand-500/50 transition-shadow">
                <Briefcase className="w-5 h-5 text-white" />
              </div>
              <div className="hidden sm:block">
                <span className="text-white font-bold text-lg leading-tight">JobMatch</span>
                <span className="text-brand-400 font-bold text-lg ml-0.5">AI</span>
              </div>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {publicNavItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? 'text-brand-400 bg-brand-500/10'
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>

            {/* Right buttons */}
            <div className="hidden md:flex items-center gap-3">
              {isAuthenticated ? (
                <div className="flex items-center gap-3">
                  <Link to="/upload-job" className="btn-accent py-2 px-4 text-xs">
                    Đăng tuyển
                  </Link>
                  <div className="relative group">
                    <button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                        {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
                      </div>
                      <span className="text-sm text-slate-300 max-w-[100px] truncate">{user?.full_name || user?.email}</span>
                      <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                    {/* Dropdown */}
                    <div className="absolute right-0 mt-2 w-48 glass-card py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                      <Link to="/dashboard" className="block px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5">Dashboard</Link>
                      <Link to="/profile" className="block px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5">Hồ sơ</Link>
                      <div className="border-t border-white/5 my-1" />
                      <button onClick={() => { logout(); navigate('/') }} className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10">
                        Đăng xuất
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <Link to="/login" className="btn-ghost text-xs">
                    <LogIn className="w-4 h-4" />
                    Đăng nhập
                  </Link>
                  <Link to="/register" className="btn-primary py-2 px-4 text-xs">
                    <UserPlus className="w-4 h-4" />
                    Đăng ký
                  </Link>
                </>
              )}
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-white/5 text-slate-400"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

          {/* Mobile menu */}
          {mobileOpen && (
            <div className="md:hidden pb-4 border-t border-white/5 mt-2 pt-3 animate-slide-down">
              {publicNavItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `block px-4 py-2.5 rounded-lg text-sm font-medium ${
                      isActive ? 'text-brand-400 bg-brand-500/10' : 'text-slate-400 hover:text-white'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
              <div className="border-t border-white/5 my-2" />
              {isAuthenticated ? (
                <button onClick={() => { logout(); navigate('/'); setMobileOpen(false) }}
                  className="block w-full text-left px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg">
                  Đăng xuất
                </button>
              ) : (
                <div className="flex gap-2 px-4">
                  <Link to="/login" onClick={() => setMobileOpen(false)} className="btn-ghost text-xs flex-1 justify-center">Đăng nhập</Link>
                  <Link to="/register" onClick={() => setMobileOpen(false)} className="btn-primary py-2 px-3 text-xs flex-1 justify-center">Đăng ký</Link>
                </div>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* ── Main Content ──────────────────────── */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* ── Footer ────────────────────────────── */}
      {!hideFooter && <Footer />}
    </div>
  )
}
