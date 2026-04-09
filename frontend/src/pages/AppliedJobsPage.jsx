import React, { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Send, Briefcase, Building2, Clock, ArrowRight, CheckCircle, Loader2, XCircle,
} from 'lucide-react'

function getAppliedJobs() {
  try { return JSON.parse(localStorage.getItem('appliedJobs') || '[]') } catch { return [] }
}

const STATUS_MAP = {
  'Đã gửi': { icon: Send, color: 'brand', bg: 'bg-brand-500/10 border-brand-500/20 text-brand-400' },
  'Đang xem xét': { icon: Loader2, color: 'amber', bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400' },
  'Phỏng vấn': { icon: CheckCircle, color: 'emerald', bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' },
  'Từ chối': { icon: XCircle, color: 'red', bg: 'bg-red-500/10 border-red-500/20 text-red-400' },
}

export default function AppliedJobsPage() {
  const appliedJobs = useMemo(() => getAppliedJobs(), [])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Send className="w-6 h-6 text-emerald-400" />
          Đã ứng tuyển
        </h2>
        <p className="text-slate-400 text-sm mt-1">Theo dõi trạng thái các đơn ứng tuyển ({appliedJobs.length})</p>
      </div>

      {appliedJobs.length > 0 ? (
        <div className="space-y-3">
          {appliedJobs.map((app, i) => {
            const statusInfo = STATUS_MAP[app.status] || STATUS_MAP['Đã gửi']
            const StatusIcon = statusInfo.icon
            return (
              <div key={i} className="glass-card p-5 hover:border-brand-500/20 transition-all duration-300 group">
                <div className="flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500/20 to-brand-500/20 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <Link to={`/jobs/${app.id}`} className="text-white font-semibold text-sm group-hover:text-brand-400 transition-colors">
                      {app.title || `Vị trí #${app.id}`}
                    </Link>
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(app.date).toLocaleDateString('vi-VN')}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${statusInfo.bg}`}>
                      <StatusIcon className="w-3 h-3" />
                      {app.status}
                    </span>
                    <Link to={`/jobs/${app.id}`} className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
                      Xem <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="glass-card p-16 text-center">
          <Send className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-white font-semibold text-lg mb-2">Chưa ứng tuyển việc nào</h3>
          <p className="text-slate-500 text-sm mb-6">Tìm kiếm và ứng tuyển các vị trí phù hợp với CV của bạn.</p>
          <Link to="/jobs" className="btn-primary">
            <Briefcase className="w-4 h-4" /> Tìm việc làm
          </Link>
        </div>
      )}
    </div>
  )
}
