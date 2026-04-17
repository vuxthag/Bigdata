import React, { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bookmark, Trash2, Briefcase, Building2, MapPin, ArrowRight, Clock,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'

function getSavedJobs() {
  try { return JSON.parse(localStorage.getItem('savedJobs') || '[]') } catch { return [] }
}
function setSavedJobs(arr) { localStorage.setItem('savedJobs', JSON.stringify(arr)) }

export default function SavedJobsPage() {
  const [savedIds, setSavedIds] = useState(getSavedJobs)

  const { data } = useQuery({
    queryKey: ['jobs-for-saved'],
    queryFn: () => jobsApi.list({ page_size: 100 }).then(r => r.data),
  })

  const savedJobs = useMemo(
    () => (data?.items || []).filter(j => savedIds.includes(j.id)),
    [data, savedIds]
  )

  const handleRemove = (jobId) => {
    const updated = savedIds.filter(id => id !== jobId)
    setSavedJobs(updated)
    setSavedIds(updated)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Bookmark className="w-6 h-6 text-brand-400" />
          Việc đã lưu
        </h2>
        <p className="text-slate-500 text-sm mt-1">Danh sách việc làm bạn đã đánh dấu ({savedIds.length})</p>
      </div>

      {savedJobs.length > 0 ? (
        <div className="space-y-3">
          {savedJobs.map(job => (
            <div key={job.id} className="glass-card p-5 hover:border-slate-200rand-500/20 transition-all duration-300 group">
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 rounded-xl bg-slate-50radient-to-br from-brand-500/20 to-purple-500/20 border border-slate-200rand-500/20 flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-5 h-5 text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <Link to={`/jobs/${job.id}`} className="text-slate-900 font-semibold text-sm group-hover:text-brand-400 transition-colors">
                    {job.position_title}
                  </Link>
                  <p className="text-slate-500 text-xs mt-0.5">{job.company_name || 'JobMatch AI'}</p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <span className="tag-fulltime">{job.job_type || 'Full-time'}</span>
                    <span className="tag"><MapPin className="w-3 h-3 mr-0.5" />{job.location || 'Việt Nam'}</span>
                  </div>
                  <p className="text-slate-500 text-xs mt-2 line-clamp-1">{job.description?.substring(0, 120) || 'Mô tả công việc...'}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <button
                    onClick={() => handleRemove(job.id)}
                    className="p-2 rounded-lg hover:bg-slate-50ed-500/10 text-slate-500 hover:text-red-400 transition-colors"
                    title="Bỏ lưu"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <Link to={`/jobs/${job.id}`} className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
                    Chi tiết <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-card p-16 text-center">
          <Bookmark className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-slate-900 font-semibold text-lg mb-2">Chưa lưu việc làm nào</h3>
          <p className="text-slate-500 text-sm mb-6">Hãy duyệt qua danh sách việc làm và nhấn lưu để xem lại sau.</p>
          <Link to="/jobs" className="btn-primary">
            <Briefcase className="w-4 h-4" /> Duyệt việc làm
          </Link>
        </div>
      )}
    </div>
  )
}
