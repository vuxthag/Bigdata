import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { employerJobsApi, employerApplicationsApi } from '../../api/employer'
import { useToast } from '../../components/employer/Toast'
import { JobStatusBadge } from '../../components/employer/StatusBadge'
import ApplicationTable from '../../components/employer/ApplicationTable'
import {
  ArrowLeft, MapPin, Clock, DollarSign, Calendar, Users, Tag,
  Zap, XCircle, Edit2, Trash2, Loader2, Save, X, Plus
} from 'lucide-react'

const JOB_TYPES = [
  { value: 'full_time',  label: 'Full-time'  },
  { value: 'part_time',  label: 'Part-time'  },
  { value: 'contract',   label: 'Hợp đồng'  },
  { value: 'internship', label: 'Thực tập'  },
  { value: 'remote',     label: 'Remote'     },
]

function formatSalary(min, max) {
  if (!min && !max) return 'Thỏa thuận'
  const fmt = n => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(0)}M` : n.toLocaleString()
  if (min && max) return `${fmt(min)} – ${fmt(max)} VND`
  if (min) return `Từ ${fmt(min)} VND`
  return `Đến ${fmt(max)} VND`
}

// ── Skill Tag Input (reused from NewJob) ─────────────────────────────────────
function SkillInput({ skills, onChange }) {
  const [input, setInput] = useState('')
  const add = () => {
    const t = input.trim()
    if (t && !skills.includes(t)) onChange([...skills, t])
    setInput('')
  }
  const remove = (s) => onChange(skills.filter(x => x !== s))
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="Nhập skill + Enter..." className="input-field flex-1 py-2 text-sm" />
        <button type="button" onClick={add} className="btn-secondary px-3"><Plus size={14}/></button>
      </div>
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {skills.map(s => (
            <span key={s} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-600/20 border border-brand-500/30 text-brand-300 text-xs font-medium">
              {s}
              <button type="button" onClick={() => remove(s)} className="hover:text-red-400 transition-colors"><X size={11}/></button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Edit Form ─────────────────────────────────────────────────────────────────
function EditForm({ job, onSave, onCancel, isSaving }) {
  const [form, setForm] = useState({
    position_title: job.position_title || '',
    description:    job.description    || '',
    location:       job.location       || '',
    job_type:       job.job_type       || 'full_time',
    salary_min:     job.salary_min     ?? '',
    salary_max:     job.salary_max     ?? '',
    deadline:       job.deadline ? job.deadline.split('T')[0] : '',
    skills:         job.skills         || [],
  })
  const set = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      position_title: form.position_title,
      description:    form.description || null,
      location:       form.location    || null,
      job_type:       form.job_type    || null,
      salary_min:     form.salary_min  ? Number(form.salary_min)  : null,
      salary_max:     form.salary_max  ? Number(form.salary_max)  : null,
      deadline:       form.deadline    || null,
      skills:         form.skills,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="glass-card p-6 space-y-5">
        <div>
          <label className="field-label">Vị trí *</label>
          <input required value={form.position_title} onChange={set('position_title')} className="input-field" />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="field-label">Địa điểm</label>
            <input value={form.location} onChange={set('location')} className="input-field" />
          </div>
          <div>
            <label className="field-label">Loại việc</label>
            <select value={form.job_type} onChange={set('job_type')} className="input-field">
              {JOB_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="field-label">Lương min (VND)</label>
            <input type="number" value={form.salary_min} onChange={set('salary_min')} min={0} className="input-field" />
          </div>
          <div>
            <label className="field-label">Lương max (VND)</label>
            <input type="number" value={form.salary_max} onChange={set('salary_max')} min={0} className="input-field" />
          </div>
          <div>
            <label className="field-label">Hạn nộp</label>
            <input type="date" value={form.deadline} onChange={set('deadline')} className="input-field" />
          </div>
        </div>
        <div>
          <label className="field-label">Mô tả</label>
          <textarea value={form.description} onChange={set('description')} rows={8} className="input-field resize-none" />
        </div>
        <div>
          <label className="field-label flex items-center gap-1.5"><Tag size={12}/> Skills</label>
          <SkillInput skills={form.skills} onChange={s => setForm(p => ({ ...p, skills: s }))} />
        </div>
      </div>
      <div className="flex gap-3">
        <button type="submit" disabled={isSaving} className="btn-primary">
          {isSaving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          Lưu thay đổi
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary">Hủy</button>
      </div>
    </form>
  )
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function OverviewTab({ job }) {
  return (
    <div className="space-y-6">
      {/* Meta row */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-400">
        {job.location && (
          <span className="flex items-center gap-2">
            <MapPin size={14} className="text-brand-400" /> {job.location}
          </span>
        )}
        {job.job_type && (
          <span className="flex items-center gap-2">
            <Clock size={14} className="text-brand-400" />
            {JOB_TYPES.find(t => t.value === job.job_type)?.label || job.job_type}
          </span>
        )}
        <span className="flex items-center gap-2">
          <DollarSign size={14} className="text-brand-400" />
          {formatSalary(job.salary_min, job.salary_max)}
        </span>
        {job.deadline && (
          <span className="flex items-center gap-2">
            <Calendar size={14} className="text-brand-400" />
            Hết hạn {new Date(job.deadline).toLocaleDateString('vi-VN')}
          </span>
        )}
        <span className="flex items-center gap-2">
          <Users size={14} className="text-brand-400" />
          {job.applicant_count ?? 0} ứng viên
        </span>
      </div>

      {/* Skills */}
      {job.skills?.length > 0 && (
        <div>
          <p className="text-slate-500 text-xs mb-2 uppercase tracking-wider font-medium">Kỹ năng yêu cầu</p>
          <div className="flex flex-wrap gap-1.5">
            {job.skills.map(s => <span key={s} className="badge-brand">{s}</span>)}
          </div>
        </div>
      )}

      {/* Description */}
      {job.description ? (
        <div>
          <p className="text-slate-500 text-xs mb-3 uppercase tracking-wider font-medium">Mô tả công việc</p>
          <div className="glass-card p-5">
            <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{job.description}</p>
          </div>
        </div>
      ) : (
        <div className="glass-card p-8 text-center">
          <p className="text-slate-500 text-sm">Chưa có mô tả</p>
        </div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function JobDetailPage() {
  const { jobId }  = useParams()
  const navigate   = useNavigate()
  const toast      = useToast()
  const qc         = useQueryClient()
  const [tab,      setTab]      = useState('overview')  // overview | applications
  const [editing,  setEditing]  = useState(false)
  const [updatingId, setUpdatingId] = useState(null)

  // Queries
  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['employer-job', jobId],
    queryFn: () => employerJobsApi.get(jobId).then(r => r.data),
    staleTime: 30_000,
  })

  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['employer-applications', jobId],
    queryFn: () => employerApplicationsApi.listByJob(jobId).then(r => r.data),
    enabled: tab === 'applications',
    staleTime: 30_000,
  })

  // Mutations
  const updateMutation = useMutation({
    mutationFn: (data) => employerJobsApi.update(jobId, data),
    onSuccess: () => {
      toast('Cập nhật thành công!', 'success')
      qc.invalidateQueries({ queryKey: ['employer-job', jobId] })
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      setEditing(false)
    },
    onError: (e) => toast(e.message, 'error'),
  })

  const publishMutation = useMutation({
    mutationFn: () => employerJobsApi.publish(jobId),
    onSuccess: () => {
      toast('Đã đăng tin! 🚀', 'success')
      qc.invalidateQueries({ queryKey: ['employer-job', jobId] })
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
    },
    onError: (e) => toast(e.message, 'error'),
  })

  const closeMutation = useMutation({
    mutationFn: () => employerJobsApi.close(jobId),
    onSuccess: () => {
      toast('Đã đóng tin', 'success')
      qc.invalidateQueries({ queryKey: ['employer-job', jobId] })
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
    },
    onError: (e) => toast(e.message, 'error'),
  })

  const statusMutation = useMutation({
    mutationFn: ({ appId, status }) => employerApplicationsApi.updateStatus(appId, status),
    onSuccess: (_, { appId }) => {
      toast('Cập nhật trạng thái!', 'success')
      qc.invalidateQueries({ queryKey: ['employer-applications', jobId] })
      setUpdatingId(null)
    },
    onError: (e) => { toast(e.message, 'error'); setUpdatingId(null) },
  })

  const handleStatusUpdate = (appId, status) => {
    setUpdatingId(appId)
    statusMutation.mutate({ appId, status })
  }

  // ── Loading skeleton ────────────────────────────────────────────────────────
  if (jobLoading) {
    return (
      <div className="max-w-4xl space-y-6 animate-pulse">
        <div className="h-8 bg-white/5 rounded w-1/3" />
        <div className="glass-card p-6 space-y-4">
          <div className="h-6 bg-white/5 rounded w-1/2" />
          <div className="flex gap-4">
            {[1,2,3].map(i => <div key={i} className="h-4 bg-white/5 rounded w-24" />)}
          </div>
          <div className="h-40 bg-white/5 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!job) return (
    <div className="glass-card p-12 text-center">
      <p className="text-slate-400">Không tìm thấy tin tuyển dụng</p>
      <Link to="/employer/jobs" className="btn-secondary mt-4 mx-auto">Quay lại</Link>
    </div>
  )

  const isActionLoading = publishMutation.isPending || closeMutation.isPending

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start gap-4">
        <button onClick={() => navigate('/employer/jobs')} className="btn-ghost p-2 mt-0.5">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{job.position_title || 'Chưa đặt tên'}</h1>
            <JobStatusBadge status={job.status} />
          </div>
          {job.company?.name && (
            <p className="text-slate-500 text-sm mt-0.5">{job.company.name}</p>
          )}
          <p className="text-small mt-1">
            Tạo {new Date(job.created_at).toLocaleDateString('vi-VN')} ·{' '}
            Cập nhật {new Date(job.updated_at).toLocaleDateString('vi-VN')}
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {job.status === 'draft' && !editing && (
            <>
              <button
                onClick={() => setEditing(true)}
                className="btn-secondary"
              >
                <Edit2 size={14} /> Chỉnh sửa
              </button>
              <button
                onClick={() => publishMutation.mutate()}
                disabled={isActionLoading}
                className="btn-primary"
              >
                {publishMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                Đăng tin
              </button>
            </>
          )}
          {job.status === 'published' && !editing && (
            <>
              <button onClick={() => setEditing(true)} className="btn-secondary">
                <Edit2 size={14} /> Chỉnh sửa
              </button>
              <button
                onClick={() => closeMutation.mutate()}
                disabled={isActionLoading}
                className="btn-secondary text-amber-400 border-amber-500/20 hover:bg-amber-500/10"
              >
                {closeMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
                Đóng tin
              </button>
            </>
          )}
        </div>
      </div>

      {/* Edit form or View */}
      {editing ? (
        <EditForm
          job={job}
          onSave={(data) => updateMutation.mutate(data)}
          onCancel={() => setEditing(false)}
          isSaving={updateMutation.isPending}
        />
      ) : (
        <>
          {/* Tabs */}
          <div className="flex bg-dark-800/80 border border-white/5 rounded-xl p-1 gap-0.5 w-fit">
            {[
              { key: 'overview',      label: 'Tổng quan'   },
              { key: 'applications',  label: `Ứng viên (${job.applicant_count ?? 0})` },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === key
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {tab === 'overview' ? (
            <OverviewTab job={job} />
          ) : (
            <ApplicationTable
              applications={appsData?.items || []}
              isLoading={appsLoading}
              onUpdateStatus={handleStatusUpdate}
              updatingId={updatingId}
            />
          )}
        </>
      )}
    </div>
  )
}
