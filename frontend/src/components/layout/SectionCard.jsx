import React from 'react'

export default function SectionCard({
  title,
  titleIcon: TitleIcon,
  titleIconColor = 'text-brand-400',
  headerRight,
  children,
  className = '',
  noPadding = false,
  gradient = false,
  gradientColor = '',
  hover = true,
}) {
  return (
    <div
      className={`
        bg-[rgba(255,255,255,0.03)] 
        border border-[rgba(255,255,255,0.08)] 
        backdrop-blur-md 
        rounded-2xl 
        shadow-lg shadow-black/10
        transition-all duration-300
        ${hover ? 'hover:border-[rgba(255,255,255,0.15)] hover:shadow-brand-500/5' : ''}
        ${gradient ? `bg-gradient-to-br ${gradientColor}` : ''}
        ${noPadding ? '' : 'p-6'}
        ${className}
      `}
    >
      {/* Card Header */}
      {(title || headerRight) && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold flex items-center gap-2">
            {TitleIcon && <TitleIcon className={`w-4 h-4 ${titleIconColor}`} />}
            {title}
          </h3>
          {headerRight}
        </div>
      )}
      {children}
    </div>
  )
}
