import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react'

const ToastCtx = createContext(null)

const ICONS = {
  success: { Icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  error:   { Icon: XCircle,      color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/20'         },
  warning: { Icon: AlertCircle,  color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20'     },
}

function ToastItem({ id, type = 'success', message, onRemove }) {
  const { Icon, color, bg } = ICONS[type] || ICONS.success

  useEffect(() => {
    const t = setTimeout(() => onRemove(id), 4000)
    return () => clearTimeout(t)
  }, [id, onRemove])

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-md
                  ${bg} animate-slide-left min-w-[280px] max-w-sm`}
    >
      <Icon size={16} className={`${color} mt-0.5 shrink-0`} />
      <p className="text-sm text-slate-200 flex-1 leading-relaxed">{message}</p>
      <button onClick={() => onRemove(id)} className="text-slate-500 hover:text-slate-300 transition-colors">
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const remove = useCallback((id) => setToasts(p => p.filter(t => t.id !== id)), [])

  const toast = useCallback((message, type = 'success') => {
    const id = Date.now()
    setToasts(p => [...p, { id, message, type }])
  }, [])

  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-[9999] pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem {...t} onRemove={remove} />
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => {
  const ctx = useContext(ToastCtx)
  if (!ctx) throw new Error('useToast must be inside ToastProvider')
  return ctx
}
