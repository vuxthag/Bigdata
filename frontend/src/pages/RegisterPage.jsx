import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Briefcase, Mail, Lock, User, Loader2 } from 'lucide-react'
import { authApi } from '../api/auth'
import useAuthStore from '../store/authStore'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.register(form)
      const token = res.data.token.access_token
      login(res.data.user, token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Đăng ký thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-brand-600/20 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md animate-slide-up">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 shadow-2xl shadow-brand-500/30 mb-4">
            <Briefcase className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">Tạo tài khoản</h1>
          <p className="text-slate-400 mt-2 text-sm">Bắt đầu tìm kiếm việc làm phù hợp</p>
        </div>

        <div className="glass-card p-8 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="field-label">Họ tên</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="text" className="input-field pl-10" placeholder="Nguyễn Văn A"
                  value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              </div>
            </div>
            <div>
              <label className="field-label">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="email" className="input-field pl-10" placeholder="you@example.com"
                  value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
            </div>
            <div>
              <label className="field-label">Mật khẩu</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" className="input-field pl-10" placeholder="Tối thiểu 6 ký tự"
                  value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={6} />
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm">{error}</div>
            )}

            <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Đang tạo tài khoản...' : 'Tạo tài khoản'}
            </button>
          </form>

          <div className="text-center text-sm text-slate-500">
            Đã có tài khoản?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Đăng nhập</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
