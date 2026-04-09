import React from 'react'

const colorMap = {
  brand:   'from-brand-500/20 to-brand-600/10 border-brand-500/30 text-brand-400',
  purple:  'from-purple-500/20 to-purple-600/10 border-purple-500/30 text-purple-400',
  emerald: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400',
  amber:   'from-amber-500/20 to-amber-600/10 border-amber-500/30 text-amber-400',
  rose:    'from-rose-500/20 to-rose-600/10 border-rose-500/30 text-rose-400',
}

export default function StatsCard({ icon: Icon, label, value, sub, color = 'brand' }) {
  return (
    <div className={`glass-card p-5 bg-gradient-to-br ${colorMap[color] || colorMap.brand} border`}>
      <div className="flex items-center gap-3 mb-3">
        {Icon && <Icon className="w-5 h-5 opacity-80" />}
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}
