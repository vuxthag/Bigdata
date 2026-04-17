import React from 'react'

const variants = {
  primary: `
    bg-slate-50radient-to-r from-brand-600 to-purple-600
    hover:from-brand-500 hover:to-purple-500
    text-slate-900 font-semibold
    shadow-lg shadow-brand-600/30
    hover:shadow-brand-500/40
    hover:-translate-y-0.5
  `,
  secondary: `
    bg-slate-100 hover:bg-slate-200
    border border-slate-200 hover:border-slate-300
    text-slate-600 hover:text-slate-900 font-medium
  `,
  accent: `
    bg-slate-50radient-to-r from-accent-500 to-accent-600
    hover:from-accent-400 hover:to-accent-500
    text-slate-900 font-semibold
    shadow-lg shadow-accent-500/30
    hover:shadow-accent-400/40
    hover:-translate-y-0.5
  `,
}

export default function GradientButton({
  variant = 'primary',
  icon: Icon,
  children,
  className = '',
  disabled = false,
  ...props
}) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2 
        px-6 py-3 rounded-xl text-sm
        transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0
        ${variants[variant] || variants.primary}
        ${className}
      `}
      disabled={disabled}
      {...props}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
    </button>
  )
}
