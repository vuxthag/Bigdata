import React, { useState } from 'react'
import { Briefcase, FileText, Loader2, Plus, CheckCircle } from 'lucide-react'
import { jobsApi } from '../api/jobs'

export default function UploadJobPage() {
  const [form, setForm] = useState({ position_title: '', description: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.position_title.trim() || !form.description.trim()) {
      setError('Vui lòng điền đầy đủ thông tin')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await jobsApi.create(form)
      setSuccess(res.data)
      setForm({ position_title: '', description: '' })
    } catch (err) {
      setError(err.message || 'Tạo job thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20">
            <Briefcase className="w-6 h-6 text-white" />
          </div>
          Đăng tin tuyển dụng
        </h1>
        <p className="text-slate-400 mt-1">Tạo mô tả công việc mới để hệ thống gợi ý ứng viên phù hợp</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Plus className="w-5 h-5 text-brand-400" />
            Thông tin công việc
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="field-label">Chức danh công việc</label>
              <input
                type="text"
                className="input-field"
                placeholder="VD: Software Engineer, Data Scientist..."
                value={form.position_title}
                onChange={(e) => setForm({ ...form, position_title: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="field-label">Mô tả công việc</label>
              <textarea
                className="input-field min-h-[200px] resize-y"
                placeholder="Nhập mô tả chi tiết về công việc, yêu cầu, kỹ năng cần thiết..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                required
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Đang tạo...' : 'Tạo công việc'}
            </button>
          </form>
        </div>

        {/* Success result */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-400" />
            Kết quả
          </h2>

          {success ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Tạo công việc thành công!</span>
              </div>
              <div className="bg-dark-600/50 rounded-xl p-4 space-y-2">
                <p className="text-sm text-slate-400">Chức danh</p>
                <p className="text-white font-medium">{success.position_title}</p>
                <p className="text-sm text-slate-400 mt-3">Mô tả</p>
                <p className="text-slate-300 text-sm">{success.description?.substring(0, 300)}...</p>
                <p className="text-sm text-slate-400 mt-3">ID</p>
                <p className="text-brand-400 text-xs font-mono">{success.id}</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-slate-500">
              <Briefcase className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">Điền thông tin và nhấn "Tạo công việc"</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
