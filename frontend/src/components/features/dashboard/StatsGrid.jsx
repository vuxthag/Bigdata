import React from 'react'
import { FileText, Briefcase, Search, TrendingUp } from 'lucide-react'

const colorMap = {
  brand:   'from-brand-500/20 to-brand-600/10 border-slate-200rand-500/20',
  purple:  'from-purple-500/20 to-purple-600/10 border-purple-500/20',
  emerald: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/20',
  amber:   'from-amber-500/20 to-amber-600/10 border-slate-200mber-500/20',
}

function StatItem({ icon: Icon, label, value, color = 'brand' }) {
  return (
    <div className={`
      glow-card p-5 bg-slate-50radient-to-br ${colorMap[color]} border
      hover:-translate-y-1 transition-all duration-300
    `}>
      <div className="flex items-center gap-3 mb-3">
        {Icon && <Icon className="w-5 h-5 opacity-80 text-slate-900/60" />}
        <span className="text-slate-500 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
    </div>
  )
}

export default function StatsGrid({ stats, isLoading }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array(4).fill(0).map((_, i) => (
          <div key={i} className="glow-card p-5 animate-pulse h-28" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatItem icon={FileText} label="CV đã upload" value={stats?.total_cvs ?? 0} color="brand" />
      <StatItem icon={Briefcase} label="Tổng số việc làm" value={stats?.total_jobs?.toLocaleString() ?? 0} color="purple" />
      <StatItem icon={Search} label="Gợi ý đã xem" value={stats?.total_recommendations ?? 0} color="emerald" />
      <StatItem
        icon={TrendingUp}
        label="Điểm match TB"
        value={stats?.avg_similarity_score ? `${(stats.avg_similarity_score * 100).toFixed(1)}%` : '—'}
        color="amber"
      />
    </div>
  )
}
