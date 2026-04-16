import React, { useState } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import { AppStatusBadge } from './StatusBadge'

const ALL_STATUSES = ['reviewed', 'interview', 'offered', 'rejected', 'hired']

const STATUS_LABELS = {
  applied:   'Đã nộp',
  reviewed:  'Đã xem',
  interview: 'Phỏng vấn',
  offered:   'Đã offer',
  rejected:  'Từ chối',
  hired:     'Đã tuyển',
}

// Valid next states per current status
const NEXT_STATUS = {
  applied:   ['reviewed', 'rejected'],
  reviewed:  ['interview', 'rejected'],
  interview: ['offered', 'rejected'],
  offered:   ['hired', 'rejected'],
  rejected:  [],
  hired:     [],
}

function StatusDropdown({ appId, current, onUpdate, isUpdating }) {
  const [open, setOpen] = useState(false)
  const nexts = NEXT_STATUS[current] || []

  if (nexts.length === 0) {
    return <AppStatusBadge status={current} />
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(p => !p)}
        disabled={isUpdating}
        className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all disabled:opacity-50"
      >
        {isUpdating ? (
          <Loader2 size={12} className="animate-spin" />
        ) : (
          <>
            <AppStatusBadge status={current} />
            <ChevronDown size={11} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
          </>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1.5 z-20 bg-dark-700 border border-white/10 rounded-xl shadow-xl min-w-[140px] py-1 animate-fade-in">
            {nexts.map(s => (
              <button
                key={s}
                onClick={() => { onUpdate(appId, s); setOpen(false) }}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
              >
                <AppStatusBadge status={s} />
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function SkeletonRow() {
  return (
    <tr className="border-b border-white/5">
      {[1,2,3,4,5].map(i => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-white/5 rounded animate-pulse" style={{ width: `${60 + i * 10}%` }} />
        </td>
      ))}
    </tr>
  )
}

export default function ApplicationTable({ applications = [], isLoading, onUpdateStatus, updatingId }) {
  if (isLoading) {
    return (
      <div className="glass-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              {['Ứng viên','Email','Ngày nộp','CV','Trạng thái'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
          </tbody>
        </table>
      </div>
    )
  }

  if (applications.length === 0) {
    return (
      <div className="glass-card p-12 flex flex-col items-center gap-3 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center">
          <span className="text-3xl">📭</span>
        </div>
        <p className="text-slate-400 text-sm">Chưa có ứng viên nào</p>
      </div>
    )
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02]">
              {['Ứng viên','Email','Ngày nộp','Cover Letter','Trạng thái'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {applications.map((app, i) => (
              <tr
                key={app.application_id}
                className={`border-b border-white/5 hover:bg-white/[0.02] transition-colors ${i % 2 === 0 ? '' : 'bg-white/[0.01]'}`}
              >
                <td className="px-4 py-3">
                  <p className="text-white font-medium">{app.candidate?.name || '—'}</p>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{app.candidate?.email || '—'}</td>
                <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                  {app.applied_at ? new Date(app.applied_at).toLocaleDateString('vi-VN') : '—'}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs max-w-[200px]">
                  {app.cover_letter
                    ? <span className="line-clamp-1 italic">"{app.cover_letter}"</span>
                    : <span className="text-slate-600">Không có</span>
                  }
                </td>
                <td className="px-4 py-3">
                  <StatusDropdown
                    appId={app.application_id}
                    current={app.status}
                    onUpdate={onUpdateStatus}
                    isUpdating={updatingId === app.application_id}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2 border-t border-white/5 bg-white/[0.01]">
        <p className="text-xs text-slate-500">{applications.length} ứng viên</p>
      </div>
    </div>
  )
}
