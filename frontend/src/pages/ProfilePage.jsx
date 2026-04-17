import React, { useState, useEffect } from 'react'
import { User, Mail, Save, Loader2, CheckCircle, Lock } from 'lucide-react'
import useAuthStore from '../store/authStore'
import { usersApi } from '../api/users'

export default function ProfilePage() {
  const { user, setUser } = useAuthStore()
  const [form, setForm] = useState({ full_name: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (user) {
      setForm({ full_name: user.full_name || '', password: '' })
    }
  }, [user])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      const payload = {}
      if (form.full_name !== (user?.full_name || '')) {
        payload.full_name = form.full_name
      }
      if (form.password) {
        payload.password = form.password
      }
      if (Object.keys(payload).length === 0) {
        setError('Không có thay đổi nào')
        setLoading(false)
        return
      }
      const res = await usersApi.updateMe(payload)
      setUser(res.data)
      setSuccess('Cập nhật thành công!')
      setForm({ ...form, password: '' })
    } catch (err) {
      setError(err.message || 'Cập nhật thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 animate-slide-up max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
          <div className="p-2 rounded-xl bg-slate-50radient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20">
            <User className="w-6 h-6 text-slate-900" />
          </div>
          Hồ sơ cá nhân
        </h1>
        <p className="text-slate-500 mt-1">Quản lý thông tin cá nhân của bạn</p>
      </div>

      {/* Profile card */}
      <div className="glass-card p-6">
        {/* User info display */}
        <div className="flex items-center gap-4 mb-6 pb-6 border-slate-200 border-slate-200">
          <div className="w-16 h-16 rounded-2xl bg-slate-50radient-to-br from-brand-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
            {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{user?.full_name || 'Chưa đặt tên'}</h2>
            <p className="text-slate-500 text-sm flex items-center gap-1">
              <Mail className="w-3.5 h-3.5" />
              {user?.email}
            </p>
            <p className="text-slate-500 text-xs mt-1">
              Tham gia: {user?.created_at ? new Date(user.created_at).toLocaleDateString('vi-VN') : '—'}
            </p>
          </div>
        </div>

        {/* Edit form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="field-label">Họ tên</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                className="input-field pl-10"
                placeholder="Nguyễn Văn A"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="field-label">Mật khẩu mới (để trống nếu không đổi)</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                className="input-field pl-10"
                placeholder="••••••••"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                minLength={6}
              />
            </div>
          </div>

          {error && (
            <div className="bg-slate-50ed-500/10 border border-slate-200ed-500/30 rounded-xl p-3 text-red-400 text-sm">{error}</div>
          )}
          {success && (
            <div className="bg-slate-50reen-500/10 border border-slate-200reen-500/30 rounded-xl p-3 text-green-400 text-sm flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              {success}
            </div>
          )}

          <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {loading ? 'Đang lưu...' : 'Lưu thay đổi'}
          </button>
        </form>
      </div>
    </div>
  )
}
