import React from 'react'
import { CheckCircle2, Clock, XCircle, AlertCircle, Star, UserCheck, Ban } from 'lucide-react'

// ── Job status badge ──────────────────────────────────────────────────────────

const JOB_STATUS = {
  draft:     { label: 'Nháp',     icon: Clock,        cls: 'badge-yellow' },
  published: { label: 'Đang mở',  icon: CheckCircle2,  cls: 'badge-green'  },
  closed:    { label: 'Đã đóng',  icon: XCircle,       cls: 'badge-gray'   },
}

export function JobStatusBadge({ status }) {
  const cfg = JOB_STATUS[status] || JOB_STATUS.draft
  const Icon = cfg.icon
  return (
    <span className={cfg.cls}>
      <Icon size={11} className="mr-1" />
      {cfg.label}
    </span>
  )
}

// ── Application status badge ──────────────────────────────────────────────────

const APP_STATUS = {
  applied:   { label: 'Đã nộp',     icon: AlertCircle, cls: 'badge-brand'  },
  reviewed:  { label: 'Đã xem',     icon: Star,        cls: 'badge-yellow' },
  interview: { label: 'Phỏng vấn',  icon: UserCheck,   cls: 'badge-accent' },
  offered:   { label: 'Đã offer',   icon: CheckCircle2, cls: 'badge-green' },
  rejected:  { label: 'Từ chối',    icon: Ban,          cls: 'badge-gray'  },
  hired:     { label: 'Đã tuyển',   icon: Star,         cls: 'badge-green' },
}

export function AppStatusBadge({ status }) {
  const cfg = APP_STATUS[status] || APP_STATUS.applied
  const Icon = cfg.icon
  return (
    <span className={cfg.cls}>
      <Icon size={11} className="mr-1" />
      {cfg.label}
    </span>
  )
}
