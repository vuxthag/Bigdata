import React from 'react'

export default function SimilarityBadge({ score }) {
  if (score >= 0.8)
    return <span className="badge-green">🟢 Rất phù hợp {(score * 100).toFixed(0)}%</span>
  if (score >= 0.6)
    return <span className="badge-yellow">🟡 Phù hợp {(score * 100).toFixed(0)}%</span>
  return <span className="badge-gray">⚪ Có thể phù hợp {(score * 100).toFixed(0)}%</span>
}
