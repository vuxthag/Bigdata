import React from 'react'

export default function PageContainer({ title, subtitle, badge, badgeIcon: BadgeIcon, actions, children, className = '' }) {
  return (
    <div className={`max-w-[1280px] mx-auto px-6 sm:px-8 py-6 space-y-8 animate-fade-in ${className}`}>
      {/* Page Header */}
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4">
          <div>
            {title && (
              <h2 className="text-2xl sm:text-3xl font-bold text-white">{title}</h2>
            )}
            {subtitle && (
              <p className="text-slate-400 text-sm mt-1.5">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {badge && (
              <span className="badge-brand text-xs flex items-center gap-1.5">
                {BadgeIcon && <BadgeIcon className="w-3 h-3" />}
                {badge}
              </span>
            )}
            {actions}
          </div>
        </div>
      )}
      {children}
    </div>
  )
}
