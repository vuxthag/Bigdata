import React from 'react'
import { Link } from 'react-router-dom'
import { Building2, MapPin, Clock, ArrowRight, Bookmark, BookmarkCheck, DollarSign } from 'lucide-react'
import SimilarityBadge from './SimilarityBadge'

export default function JobCard({
  job,
  showAIScore = false,
  isSaved = false,
  onSave,
  onRemove,
  compact = false,
}) {
  const {
    id,
    job_id,
    position_title,
    description,
    description_preview,
    company_name,
    location,
    salary,
    job_type,
    similarity_score,
  } = job

  const jobId = id || job_id
  const desc = description_preview || description || ''

  return (
    <div className="glass-card p-5 hover:border-brand-500/20 hover:-translate-y-0.5 transition-all duration-300 group">
      <div className="flex items-start gap-4">
        {/* Company Logo placeholder */}
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-5 h-5 text-brand-400" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Title */}
          <Link
            to={`/jobs/${jobId}`}
            className="text-white font-semibold text-sm group-hover:text-brand-400 transition-colors line-clamp-1 block"
          >
            {position_title}
          </Link>

          {/* Company */}
          <p className="text-slate-500 text-xs mt-0.5">
            {company_name || 'JobMatch AI'}
          </p>

          {/* Tags row */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {job_type && (
              <span className={
                job_type === 'Remote' ? 'tag-remote' :
                job_type === 'Intern' ? 'tag-intern' :
                job_type === 'Part-time' ? 'tag-parttime' :
                'tag-fulltime'
              }>
                {job_type}
              </span>
            )}
            {!job_type && <span className="tag-fulltime">Full-time</span>}
            {location && (
              <span className="tag">
                <MapPin className="w-3 h-3 mr-0.5" />
                {location}
              </span>
            )}
            {salary && (
              <span className="tag">
                <DollarSign className="w-3 h-3 mr-0.5" />
                {salary}
              </span>
            )}
          </div>
        </div>

        {/* AI Score or Save */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          {showAIScore && similarity_score != null && (
            <SimilarityBadge score={similarity_score} />
          )}
          {onSave && (
            <button
              onClick={(e) => { e.preventDefault(); isSaved ? onRemove?.(jobId) : onSave(jobId) }}
              className="p-1.5 rounded-lg hover:bg-white/10 text-slate-500 hover:text-brand-400 transition-colors"
              title={isSaved ? 'Bỏ lưu' : 'Lưu việc làm'}
            >
              {isSaved
                ? <BookmarkCheck className="w-4 h-4 text-brand-400" />
                : <Bookmark className="w-4 h-4" />
              }
            </button>
          )}
        </div>
      </div>

      {/* Description preview */}
      {!compact && (
        <p className="text-slate-500 text-xs mt-3 line-clamp-2 leading-relaxed">
          {desc.substring(0, 180) || 'Mô tả công việc...'}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
        <span className="text-slate-600 text-xs flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Đăng gần đây
        </span>
        <Link
          to={`/jobs/${jobId}`}
          className="text-brand-400 text-xs font-medium hover:text-brand-300 flex items-center gap-1"
        >
          Xem chi tiết <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
    </div>
  )
}
