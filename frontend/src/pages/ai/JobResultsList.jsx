import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, CheckCircle, XCircle } from 'lucide-react'
import { recommendApi } from '../../api/recommend'
import SimilarityBadge from '../../components/ui/SimilarityBadge'

/* ── Mock skill analysis ───── */
function analyzeSkills(jobDesc) {
  const allSkills = [
    'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'SQL',
    'Docker', 'AWS', 'Machine Learning', 'Git', 'REST API', 'Agile',
    'TypeScript', 'FastAPI', 'PostgreSQL', 'MongoDB',
  ]
  const desc = (jobDesc || '').toLowerCase()
  const found = allSkills.filter(s => desc.includes(s.toLowerCase()))
  const matching = found.slice(0, Math.ceil(found.length * 0.6))
  const missing = found.slice(Math.ceil(found.length * 0.6))
  if (matching.length === 0) return { matching: ['Communication', 'Teamwork'], missing: ['Python', 'SQL'] }
  return { matching, missing }
}

function JobCard({ job, rank, cvId }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const { matching, missing } = analyzeSkills(job.description_preview || job.position_title)

  const feedbackMutation = useMutation({
    mutationFn: (action) => recommendApi.feedback({ job_id: job.job_id, action, cv_id: cvId, similarity_score: job.similarity_score }),
    onSuccess: (_, action) => setFeedback(action),
  })

  return (
    <div className="glow-card p-5 hover:border-slate-200rand-500/20 transition-all duration-200 animate-slide-up">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-lg bg-slate-50radient-to-br from-brand-500/30 to-purple-500/20 border border-slate-200rand-500/30 flex items-center justify-center text-brand-400 text-xs font-bold flex-shrink-0">#{rank}</span>
          <div>
            <h3 className="text-slate-900 font-semibold text-sm leading-snug">{job.position_title}</h3>
            <p className="text-slate-500 text-xs mt-0.5">{job.company_name || 'JobMatch AI'}</p>
          </div>
        </div>
        <SimilarityBadge score={job.similarity_score} />
      </div>

      <p className="text-slate-500 text-sm leading-relaxed">
        {expanded ? job.description_preview : job.description_preview?.slice(0, 150) + (job.description_preview?.length > 150 ? '...' : '')}
      </p>
      {job.description_preview?.length > 150 && (
        <button onClick={() => setExpanded(!expanded)} className="text-brand-400 text-xs mt-1 flex items-center gap-1 hover:text-brand-300">
          {expanded ? <><ChevronUp className="w-3 h-3" /> Thu gọn</> : <><ChevronDown className="w-3 h-3" /> Xem thêm</>}
        </button>
      )}

      {/* Skills */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-3">
          <p className="text-emerald-400 text-xs font-medium flex items-center gap-1 mb-2">
            <CheckCircle className="w-3 h-3" /> Kỹ năng phù hợp ({matching.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {matching.map(s => (
              <span key={s} className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{s}</span>
            ))}
          </div>
        </div>
        <div className="bg-slate-50mber-500/5 border border-slate-200mber-500/20 rounded-xl p-3">
          <p className="text-amber-400 text-xs font-medium flex items-center gap-1 mb-2">
            <XCircle className="w-3 h-3" /> Cần bổ sung ({missing.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {missing.map(s => (
              <span key={s} className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-slate-50mber-500/10 text-amber-400 border border-slate-200mber-500/20">{s}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Feedback */}
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-200">
        {feedback ? (
          <span className="text-emerald-400 text-xs flex items-center gap-1">✓ Đã ghi nhận — <span className="capitalize">{feedback}</span></span>
        ) : (
          <>
            <button onClick={() => feedbackMutation.mutate('applied')} disabled={feedbackMutation.isPending}
              className="btn-primary py-2 px-3 text-xs from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 shadow-emerald-600/20">
              💼 Ứng tuyển
            </button>
            <button onClick={() => feedbackMutation.mutate('saved')} disabled={feedbackMutation.isPending}
              className="btn-secondary py-2 px-3 text-xs">
              🔖 Lưu lại
            </button>
            <button onClick={() => feedbackMutation.mutate('skipped')} disabled={feedbackMutation.isPending}
              className="p-2 rounded-lg hover:bg-slate-50ed-500/10 text-slate-500 hover:text-red-400 transition-colors text-xs">
              ✕ Bỏ qua
            </button>
            {job.job_id && (
              <Link to={`/jobs/${job.job_id}`} className="ml-auto text-brand-400 text-xs hover:text-brand-300">
                Xem chi tiết →
              </Link>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function JobResultsList({ results, cvId }) {
  return (
    <div className="space-y-4">
      {results.map((item, i) => (
        <JobCard key={item.job_id || i} job={item} rank={i + 1} cvId={cvId} />
      ))}
    </div>
  )
}
