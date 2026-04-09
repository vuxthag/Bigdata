import React from 'react'
import SimilarityBadge from '../../components/SimilarityBadge'

function CandidateCard({ candidate, rank }) {
  return (
    <div className="glow-card p-5 animate-slide-up">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500/30 to-brand-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 text-xs font-bold flex-shrink-0">#{rank}</span>
          <div>
            <h3 className="text-white font-semibold text-sm">{candidate.cv_filename || `CV #${candidate.cv_id}`}</h3>
            <p className="text-slate-500 text-xs">Ứng viên tiềm năng</p>
          </div>
        </div>
        <SimilarityBadge score={candidate.similarity_score} />
      </div>
      <p className="text-slate-400 text-sm leading-relaxed line-clamp-3">
        {candidate.cv_preview || candidate.description_preview || 'Xem chi tiết CV để biết thêm thông tin...'}
      </p>
    </div>
  )
}

export default function CandidateResultsList({ results }) {
  return (
    <div className="space-y-4">
      {results.map((item, i) => (
        <CandidateCard key={item.cv_id || i} candidate={item} rank={i + 1} />
      ))}
    </div>
  )
}
