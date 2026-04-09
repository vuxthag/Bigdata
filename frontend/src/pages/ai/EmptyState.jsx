import React from 'react'

export default function EmptyState({ icon: Icon, message, className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-brand-400/50" />
        </div>
      )}
      <p className="text-slate-500 text-sm max-w-xs">{message}</p>
    </div>
  )
}
