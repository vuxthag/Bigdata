import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  ChevronDown, ChevronUp, CheckCircle, XCircle,
  MapPin, Building2, Banknote, Star,
} from 'lucide-react'
import { recommendApi } from '../../api/recommend'
import SimilarityBadge from '../../components/ui/SimilarityBadge'

/* ── Skill tag lists ─────────────────────────────── */
function SkillTags({ skills, variant = 'match' }) {
  const [showAll, setShowAll] = useState(false)
  if (!skills || skills.length === 0) return null

  const display = showAll ? skills : skills.slice(0, 5)
  const rest = skills.length - 5

  const colorMap = {
    match:   'bg-emerald-500/10 text-emerald-600 border-emerald-500/25',
    missing: 'bg-amber-500/10 text-amber-600 border-amber-500/25',
  }
  const cls = colorMap[variant]

  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {display.map(s => (
        <span key={s} className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs border font-medium ${cls}`}>
          {s}
        </span>
      ))}
      {!showAll && rest > 0 && (
        <button
          onClick={() => setShowAll(true)}
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs border font-medium cursor-pointer opacity-70 hover:opacity-100 ${cls}`}
        >
          +{rest} more
        </button>
      )}
    </div>
  )
}

/* ── Score bar ─────────────────────────────────── */
function ScoreBar({ label, value, color = 'bg-brand-500' }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-500 w-20 shrink-0 truncate">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${(value * 100).toFixed(0)}%` }} />
      </div>
      <span className="text-slate-600 w-8 text-right">{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

/* ── Job Card ──────────────────────────────────── */
function JobCard({ job, rank, cvId }) {
  const [expanded, setExpanded] = useState(false)
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [feedback, setFeedback] = useState(null)

  // Use real matched/missing skills from API
  const matchedSkills = job.matched_skills || []
  const missingSkills = (job.missing_skills || []).slice(0, 8) // show top 8 missing

  const score = job.final_score ?? job.similarity_score ?? 0
  const breakdown = job.score_breakdown

  const feedbackMutation = useMutation({
    mutationFn: (action) =>
      recommendApi.feedback({ job_id: job.job_id, action, cv_id: cvId, similarity_score: score }),
    onSuccess: (_, action) => setFeedback(action),
  })

  return (
    <div className="glass-card p-5 hover:border-brand-200 transition-all duration-200 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500/30 to-purple-500/20 border border-brand-500/30 flex items-center justify-center text-brand-500 text-xs font-bold flex-shrink-0">
            #{rank}
          </span>
          <div>
            <h3 className="text-slate-900 font-semibold text-sm leading-snug">{job.position_title}</h3>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {job.company && (
                <span className="text-slate-500 text-xs flex items-center gap-1">
                  <Building2 className="w-3 h-3" />{job.company}
                </span>
              )}
              {job.location && (
                <span className="text-slate-500 text-xs flex items-center gap-1">
                  <MapPin className="w-3 h-3" />{job.location}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <SimilarityBadge score={score} />
          {job.pretty_salary && (
            <span className="text-xs text-emerald-600 flex items-center gap-1 font-medium">
              <Banknote className="w-3 h-3" />{job.pretty_salary}
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-slate-600 text-xs leading-relaxed">
        {expanded
          ? job.description_preview
          : (job.description_preview || '').slice(0, 160) + ((job.description_preview || '').length > 160 ? '...' : '')}
      </p>
      {(job.description_preview || '').length > 160 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-brand-400 text-xs mt-1 flex items-center gap-1 hover:text-brand-300"
        >
          {expanded ? <><ChevronUp className="w-3 h-3" />Thu gọn</> : <><ChevronDown className="w-3 h-3" />Xem thêm</>}
        </button>
      )}

      {/* Real Skills from API */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-3">
          <p className="text-emerald-600 text-xs font-semibold flex items-center gap-1 mb-2">
            <CheckCircle className="w-3 h-3" /> Kỹ năng phù hợp ({matchedSkills.length})
          </p>
          {matchedSkills.length > 0
            ? <SkillTags skills={matchedSkills} variant="match" />
            : <p className="text-xs text-slate-400 italic">Chưa phát hiện kỹ năng khớp</p>
          }
        </div>
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">
          <p className="text-amber-600 text-xs font-semibold flex items-center gap-1 mb-2">
            <XCircle className="w-3 h-3" /> Cần bổ sung ({missingSkills.length})
          </p>
          {missingSkills.length > 0
            ? <SkillTags skills={missingSkills} variant="missing" />
            : <p className="text-xs text-slate-400 italic">Xuất sắc! Bạn đã có đủ kỹ năng</p>
          }
        </div>
      </div>

      {/* Score Breakdown (collapsible) */}
      {breakdown && (
        <div className="mt-3">
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="text-slate-400 text-xs flex items-center gap-1 hover:text-slate-600 transition-colors"
          >
            <Star className="w-3 h-3" />
            {showBreakdown ? 'Ẩn' : 'Xem'} chi tiết điểm số
            {showBreakdown ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {showBreakdown && (
            <div className="mt-2 space-y-1.5 p-3 bg-slate-50 rounded-xl">
              <ScoreBar label="Ngữ nghĩa"   value={breakdown.cosine_similarity} color="bg-brand-500" />
              <ScoreBar label="Kỹ năng"     value={breakdown.skill_overlap}     color="bg-purple-500" />
              <ScoreBar label="Tương tác"   value={breakdown.interaction_bonus} color="bg-cyan-500" />
              <ScoreBar label="Kinh nghiệm" value={breakdown.years_match}       color="bg-emerald-500" />
              <ScoreBar label="Cấp bậc"     value={breakdown.level_match}       color="bg-amber-500" />
              <ScoreBar label="Học vấn"     value={breakdown.education_match}   color="bg-rose-400" />
            </div>
          )}
        </div>
      )}

      {/* Feedback */}
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        {feedback ? (
          <span className="text-emerald-500 text-xs flex items-center gap-1">
            ✓ Đã ghi nhận — <span className="capitalize">{feedback}</span>
          </span>
        ) : (
          <>
            <button
              onClick={() => feedbackMutation.mutate('applied')}
              disabled={feedbackMutation.isPending}
              className="btn-primary py-2 px-3 text-xs from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 shadow-emerald-600/20"
            >
              💼 Ứng tuyển
            </button>
            <button
              onClick={() => feedbackMutation.mutate('saved')}
              disabled={feedbackMutation.isPending}
              className="btn-secondary py-2 px-3 text-xs"
            >
              🔖 Lưu lại
            </button>
            <button
              onClick={() => feedbackMutation.mutate('skipped')}
              disabled={feedbackMutation.isPending}
              className="p-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors text-xs"
            >
              ✕ Bỏ qua
            </button>
            {job.job_id && (
              <Link
                to={`/jobs/${job.job_id}`}
                className="ml-auto text-brand-400 text-xs hover:text-brand-300"
              >
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
