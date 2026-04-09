import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Building2, MapPin, Clock, DollarSign, Briefcase, ArrowLeft,
  Bookmark, BookmarkCheck, Send, Share2, ExternalLink, CheckCircle, XCircle,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'
import SimilarityBadge from '../components/SimilarityBadge'
import JobCard from '../components/JobCard'

/* ── Helpers ────────────────────────────────── */
function getSavedJobs() {
  try { return JSON.parse(localStorage.getItem('savedJobs') || '[]') } catch { return [] }
}
function setSavedJobs(arr) { localStorage.setItem('savedJobs', JSON.stringify(arr)) }

function getAppliedJobs() {
  try { return JSON.parse(localStorage.getItem('appliedJobs') || '[]') } catch { return [] }
}
function setAppliedJobs(arr) { localStorage.setItem('appliedJobs', JSON.stringify(arr)) }

/* ── Mock skills extracted from description ── */
function extractSkills(text) {
  if (!text) return []
  const skillKeywords = [
    'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'SQL', 'PostgreSQL',
    'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure', 'Machine Learning',
    'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP', 'Data Science',
    'FastAPI', 'Django', 'Flask', 'Git', 'CI/CD', 'REST API', 'GraphQL',
    'TypeScript', 'HTML', 'CSS', 'Tailwind', 'MongoDB', 'Redis',
    'Agile', 'Scrum', 'Linux', 'C++', 'Go', 'Rust', 'Spark', 'Hadoop',
  ]
  return skillKeywords.filter(s => text.toLowerCase().includes(s.toLowerCase())).slice(0, 12)
}

/* ── Component ──────────────────────────────── */
export default function JobDetailPage() {
  const { jobId } = useParams()
  const [saved, setSaved] = useState(() => getSavedJobs().includes(Number(jobId)))
  const [applied, setApplied] = useState(() => getAppliedJobs().some(a => a.id === Number(jobId)))

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ['job-detail', jobId],
    queryFn: () => jobsApi.get(jobId).then(r => r.data),
    enabled: !!jobId,
  })

  const { data: relatedData } = useQuery({
    queryKey: ['jobs-list-related'],
    queryFn: () => jobsApi.list({ page_size: 4 }).then(r => r.data),
  })

  const relatedJobs = (relatedData?.items || []).filter(j => j.id !== Number(jobId)).slice(0, 3)
  const skills = extractSkills(job?.description || job?.position_title || '')

  const handleSave = () => {
    const list = getSavedJobs()
    if (saved) {
      setSavedJobs(list.filter(id => id !== Number(jobId)))
    } else {
      list.push(Number(jobId))
      setSavedJobs(list)
    }
    setSaved(!saved)
  }

  const handleApply = () => {
    if (applied) return
    const list = getAppliedJobs()
    list.push({ id: Number(jobId), title: job?.position_title, date: new Date().toISOString(), status: 'Đã gửi' })
    setAppliedJobs(list)
    setApplied(true)
  }

  /* ── Loading & Error states ─────────────── */
  if (isLoading) {
    return (
      <div className="section-container py-10 animate-fade-in">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="glass-card p-8 animate-pulse h-64 bg-dark-700/50" />
          <div className="glass-card p-6 animate-pulse h-48 bg-dark-700/50" />
        </div>
      </div>
    )
  }

  if (isError || !job) {
    return (
      <div className="section-container py-20 text-center">
        <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <h2 className="text-white text-xl font-bold mb-2">Không tìm thấy việc làm</h2>
        <p className="text-slate-500 text-sm mb-6">Việc làm này không tồn tại hoặc đã bị xóa.</p>
        <Link to="/jobs" className="btn-primary">
          <ArrowLeft className="w-4 h-4" /> Quay lại danh sách
        </Link>
      </div>
    )
  }

  return (
    <div className="section-container py-10 animate-fade-in">
      <div className="max-w-4xl mx-auto">
        {/* Back button */}
        <Link to="/jobs" className="inline-flex items-center gap-1.5 text-slate-400 hover:text-white text-sm mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Quay lại tìm kiếm
        </Link>

        {/* ── Main Card ──────────────────── */}
        <div className="glass-card p-6 sm:p-8 mb-6">
          <div className="flex flex-col sm:flex-row items-start gap-5">
            {/* Company logo */}
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-8 h-8 text-brand-400" />
            </div>

            <div className="flex-1 min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-white leading-tight">
                {job.position_title}
              </h1>
              <p className="text-brand-400 font-medium mt-1">
                {job.company_name || 'JobMatch AI'}
              </p>

              {/* Meta row */}
              <div className="flex items-center gap-3 mt-3 flex-wrap text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" /> {job.location || 'Việt Nam'}
                </span>
                <span className="flex items-center gap-1">
                  <Briefcase className="w-3.5 h-3.5" /> {job.job_type || 'Full-time'}
                </span>
                {job.salary && (
                  <span className="flex items-center gap-1">
                    <DollarSign className="w-3.5 h-3.5" /> {job.salary}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> Đăng gần đây
                </span>
              </div>
            </div>

            {/* AI match */}
            {job.similarity_score != null && (
              <SimilarityBadge score={job.similarity_score} />
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3 mt-6 pt-5 border-t border-white/5 flex-wrap">
            <button
              onClick={handleApply}
              disabled={applied}
              className={applied
                ? 'btn-primary from-emerald-600 to-emerald-700 opacity-80 cursor-default'
                : 'btn-accent'}
            >
              {applied ? <CheckCircle className="w-4 h-4" /> : <Send className="w-4 h-4" />}
              {applied ? 'Đã ứng tuyển' : 'Ứng tuyển ngay'}
            </button>

            <button onClick={handleSave} className="btn-secondary">
              {saved
                ? <><BookmarkCheck className="w-4 h-4 text-brand-400" /> Đã lưu</>
                : <><Bookmark className="w-4 h-4" /> Lưu việc làm</>}
            </button>

            <button
              onClick={() => navigator.clipboard?.writeText(window.location.href)}
              className="btn-ghost"
            >
              <Share2 className="w-4 h-4" /> Chia sẻ
            </button>
          </div>
        </div>

        {/* ── Content Grid ───────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Description */}
          <div className="lg:col-span-2 space-y-6">
            {/* Job Description */}
            <div className="glass-card p-6">
              <h2 className="text-white font-semibold text-lg mb-4">Mô tả công việc</h2>
              <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">
                {job.description || 'Chưa có mô tả chi tiết.'}
              </div>
            </div>

            {/* Skills Required */}
            {skills.length > 0 && (
              <div className="glass-card p-6">
                <h2 className="text-white font-semibold text-lg mb-4">Kỹ năng yêu cầu</h2>
                <div className="flex flex-wrap gap-2">
                  {skills.map(skill => (
                    <span key={skill} className="badge-brand">{skill}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Company Info */}
          <div className="space-y-6">
            <div className="glass-card p-6">
              <h3 className="text-white font-semibold mb-4">Thông tin công ty</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-brand-400" />
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">{job.company_name || 'JobMatch AI'}</p>
                    <p className="text-slate-500 text-xs">Công nghệ thông tin</p>
                  </div>
                </div>
                <div className="space-y-2 pt-2">
                  <div className="flex items-center gap-2 text-slate-400 text-sm">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    {job.location || 'Việt Nam'}
                  </div>
                  <div className="flex items-center gap-2 text-slate-400 text-sm">
                    <Briefcase className="w-3.5 h-3.5 text-slate-500" />
                    50-200 nhân viên
                  </div>
                </div>
                <Link
                  to={`/companies/${job.company_name || 'jobmatch-ai'}`}
                  className="text-brand-400 text-xs font-medium hover:text-brand-300 flex items-center gap-1 mt-2"
                >
                  Xem trang công ty <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* Quick stats */}
            <div className="glass-card p-6">
              <h3 className="text-white font-semibold mb-4">Tổng quan</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between text-slate-400">
                  <span>Loại</span>
                  <span className="text-white">{job.job_type || 'Full-time'}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Kinh nghiệm</span>
                  <span className="text-white">{job.experience || '1-3 năm'}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Mức lương</span>
                  <span className="text-white">{job.salary || 'Thỏa thuận'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Related Jobs ───────────────── */}
        {relatedJobs.length > 0 && (
          <div className="mt-10">
            <h2 className="section-heading mb-4">Việc làm liên quan</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {relatedJobs.map(j => (
                <JobCard key={j.id} job={j} compact />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
