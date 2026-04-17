import React from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Send, Building2, ArrowRight, Clock } from 'lucide-react'
import SectionCard from '../../layout/SectionCard'

export default function SavedJobsCard({ savedJobs, savedJobIds, appliedJobsList }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Saved Jobs */}
      <SectionCard
        title={`Việc đã lưu (${savedJobIds.length})`}
        titleIcon={Bookmark}
        titleIconColor="text-brand-400"
        headerRight={
          savedJobIds.length > 0 && (
            <Link to="/saved-jobs" className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
              Xem tất cả <ArrowRight className="w-3 h-3" />
            </Link>
          )
        }
      >
        {savedJobs.length > 0 ? (
          <div className="space-y-3">
            {savedJobs.map(job => (
              <Link key={job.id} to={`/jobs/${job.id}`}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 transition-colors group">
                <div className="w-9 h-9 rounded-lg bg-slate-50rand-500/10 border border-slate-200rand-500/20 flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-4 h-4 text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-slate-900 text-sm font-medium truncate">{job.position_title}</p>
                  <p className="text-slate-500 text-xs">{job.company_name || 'JobMatch AI'}</p>
                </div>
                <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-brand-400 transition-colors" />
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm text-center py-4">Chưa lưu việc làm nào. Hãy khám phá tại trang Việc làm!</p>
        )}
      </SectionCard>

      {/* Applied Jobs */}
      <SectionCard
        title={`Đã ứng tuyển (${appliedJobsList.length})`}
        titleIcon={Send}
        titleIconColor="text-emerald-400"
        headerRight={
          appliedJobsList.length > 0 && (
            <Link to="/applied-jobs" className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
              Xem tất cả <ArrowRight className="w-3 h-3" />
            </Link>
          )
        }
      >
        {appliedJobsList.length > 0 ? (
          <div className="space-y-3">
            {appliedJobsList.slice(0, 3).map((app, i) => (
              <Link key={i} to={`/jobs/${app.id}`}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 transition-colors group">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <Send className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-slate-900 text-sm font-medium truncate">{app.title}</p>
                  <p className="text-slate-500 text-xs flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(app.date).toLocaleDateString('vi-VN')}
                  </p>
                </div>
                <span className="badge-green text-xs">{app.status}</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm text-center py-4">Chưa ứng tuyển việc nào.</p>
        )}
      </SectionCard>
    </div>
  )
}
