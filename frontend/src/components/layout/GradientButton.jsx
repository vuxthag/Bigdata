import React from 'react'

const variants = {
  primary: `
    bg-gradient-to-r from-brand-600 to-purple-600
    hover:from-brand-500 hover:to-purple-500
    text-white font-semibold
    shadow-lg shadow-brand-600/30
    hover:shadow-brand-500/40
    hover:-translate-y-0.5
  `,
  secondary: `
    bg-white/5 hover:bg-white/10
    border border-white/10 hover:border-white/20
    text-slate-300 hover:text-white font-medium
  `,
  accent: `
    bg-gradient-to-r from-accent-500 to-accent-600
    hover:from-accent-400 hover:to-accent-500
    text-white font-semibold
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
