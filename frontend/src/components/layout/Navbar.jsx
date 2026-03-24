import React from 'react'
import { LogOut, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { authApi } from '../../api/auth'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try { await authApi.logout() } catch {}
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-20 bg-dark-800/80 backdrop-blur-xl border-b border-white/5 px-6 py-4 flex items-center justify-between">
      <div />
      <div className="flex items-center gap-4">
        {/* User info */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="hidden sm:block">
            <p className="text-white text-sm font-medium leading-tight">
              {user?.full_name || user?.email?.split('@')[0] || 'User'}
            </p>
            <p className="text-slate-500 text-xs">{user?.email}</p>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="btn-secondary px-3 py-2"
          title="Đăng xuất"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
