import React from 'react'
import { Link } from 'react-router-dom'
import { MapPin, Clock, DollarSign, Users, Zap, ChevronRight, Trash2 } from 'lucide-react'
import { JobStatusBadge } from './StatusBadge'

const JOB_TYPE_LABELS = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  contract: 'Hợp đồng',
  internship: 'Thực tập',
  remote: 'Remote',
}

function formatSalary(min, max) {
  if (!min && !max) return null
  const fmt = (n) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(0)}M` : `${n.toLocaleString()}`
  if (min && max) return `${fmt(min)} – ${fmt(max)} VND`
  if (min) return `Từ ${fmt(min)} VND`
  return `Đến ${fmt(max)} VND`
}

export default function JobCard({ job, onPublish, onClose, onDelete, isLoading }) {
  const salary = formatSalary(job.salary_min, job.salary_max)
  const canPublish = job.status === 'draft'
  const canClose   = job.status === 'published'
  const canDelete  = job.status === 'draft'

  return (
    <div className="glass-card p-5 flex flex-col gap-4 hover:border-white/20 transition-all duration-200 group">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            to={`/employer/jobs/${job.id}`}
            className="text-white font-semibold text-base hover:text-brand-400 transition-colors line-clamp-1 group-hover:text-brand-300"
          >
            {job.position_title || 'Chưa có tiêu đề'}
          </Link>
          {job.company?.name && (
            <p className="text-slate-500 text-xs mt-0.5">{job.company.name}</p>
          )}
        </div>
        <JobStatusBadge status={job.status} />
      </div>

      {/* Meta */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-400">
        {job.location && (
          <span className="flex items-center gap-1.5">
            <MapPin size={12} className="text-slate-500" />
            {job.location}
          </span>
        )}
        {job.job_type && (
          <span className="flex items-center gap-1.5">
            <Clock size={12} className="text-slate-500" />
            {JOB_TYPE_LABELS[job.job_type] || job.job_type}
          </span>
        )}
        {salary && (
          <span className="flex items-center gap-1.5">
            <DollarSign size={12} className="text-slate-500" />
            {salary}
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <Users size={12} className="text-slate-500" />
          {job.applicant_count ?? 0} ứng viên
        </span>
      </div>

      {/* Skills */}
      {job.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {job.skills.slice(0, 5).map(s => (
            <span key={s} className="tag">{s}</span>
          ))}
          {job.skills.length > 5 && (
            <span className="tag text-slate-600">+{job.skills.length - 5}</span>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t border-white/5">
        <Link
          to={`/employer/jobs/${job.id}`}
          className="btn-ghost text-xs px-3 py-1.5"
        >
          <ChevronRight size={13} />
          Chi tiết
        </Link>

        {canPublish && (
          <button
            onClick={() => onPublish?.(job.id)}
            disabled={isLoading}
            className="btn-primary text-xs px-3 py-1.5 ml-auto"
          >
            <Zap size={13} />
            Đăng tin
          </button>
        )}

        {canClose && (
          <button
            onClick={() => onClose?.(job.id)}
            disabled={isLoading}
            className="btn-secondary text-xs px-3 py-1.5 ml-auto"
          >
            Đóng
          </button>
        )}

        {canDelete && (
          <button
            onClick={() => onDelete?.(job.id)}
            disabled={isLoading}
            className="btn-ghost text-red-400 hover:text-red-300 text-xs px-2 py-1.5 ml-auto"
            title="Xóa job"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>
    </div>
  )
}
