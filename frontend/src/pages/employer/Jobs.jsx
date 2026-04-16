import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { employerJobsApi } from '../../api/employer'
import { useToast } from '../../components/employer/Toast'
import JobCard from '../../components/employer/JobCard'
import { Plus, Briefcase, Filter, Search, Loader2, RefreshCw } from 'lucide-react'

const STATUS_TABS = [
  { key: null,        label: 'Tất cả'  },
  { key: 'draft',     label: 'Nháp'    },
  { key: 'published', label: 'Đang mở' },
  { key: 'closed',    label: 'Đã đóng' },
]

function SkeletonCard() {
  return (
    <div className="glass-card p-5 space-y-3 animate-pulse">
      <div className="flex justify-between">
        <div className="h-5 bg-white/5 rounded w-2/5" />
        <div className="h-5 bg-white/5 rounded-full w-16" />
      </div>
      <div className="flex gap-4">
        {[1,2,3].map(i => <div key={i} className="h-3 bg-white/5 rounded w-20" />)}
      </div>
      <div className="flex gap-2">
        {[1,2].map(i => <div key={i} className="h-5 bg-white/5 rounded-md w-14" />)}
      </div>
      <div className="flex gap-2 pt-2 border-t border-white/5">
        <div className="h-7 bg-white/5 rounded-lg w-20" />
        <div className="h-7 bg-white/5 rounded-lg w-20 ml-auto" />
      </div>
    </div>
  )
}

export default function JobsPage() {
  const toast      = useToast()
  const qc         = useQueryClient()
  const [tab,      setTab]      = useState(null)
  const [search,   setSearch]   = useState('')
  const [loadingId, setLoadingId] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['employer-jobs', tab],
    queryFn: () =>
      employerJobsApi
        .list({ status: tab || undefined, page_size: 100 })
        .then(r => r.data),
    staleTime: 30_000,
  })

  // Filter by search
  const items = (data?.items || []).filter(j =>
    !search || j.position_title?.toLowerCase().includes(search.toLowerCase())
  )

  // ── Mutations ────────────────────────────────────────────────────────────────
  const withLoading = (id, fn) => async () => {
    setLoadingId(id)
    try { await fn() } finally { setLoadingId(null) }
  }

  const publishMutation = useMutation({
    mutationFn: (id) => employerJobsApi.publish(id),
    onSuccess: (_, id) => {
      toast('Đã đăng tin thành công! 🚀', 'success')
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
    },
    onError: (e) => toast(e.message, 'error'),
    onSettled: () => setLoadingId(null),
  })

  const closeMutation = useMutation({
    mutationFn: (id) => employerJobsApi.close(id),
    onSuccess: () => {
      toast('Đã đóng tin tuyển dụng', 'success')
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
    },
    onError: (e) => toast(e.message, 'error'),
    onSettled: () => setLoadingId(null),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => employerJobsApi.delete(id),
    onSuccess: () => {
      toast('Đã xóa tin nháp', 'success')
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
    },
    onError: (e) => toast(e.message, 'error'),
    onSettled: () => setLoadingId(null),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Briefcase size={26} className="text-brand-400" />
            Tin tuyển dụng
          </h1>
          <p className="page-subtitle">
            {data ? `${data.total} tin tổng · ${items.length} hiển thị` : 'Đang tải...'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="btn-ghost p-2"
            title="Refresh"
          >
            <RefreshCw size={15} />
          </button>
          <Link to="/employer/jobs/new" className="btn-primary">
            <Plus size={16} /> Đăng tin mới
          </Link>
        </div>
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status tabs */}
        <div className="flex bg-dark-800/80 border border-white/5 rounded-xl p-1 gap-0.5">
          {STATUS_TABS.map(({ key, label }) => (
            <button
              key={String(key)}
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                tab === key
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative ml-auto">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Tìm theo tên vị trí..."
            className="input-field pl-9 py-2 text-xs w-56"
          />
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <div className="glass-card p-16 flex flex-col items-center gap-4 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-500/20 flex items-center justify-center">
            <Briefcase size={24} className="text-brand-400" />
          </div>
          <div>
            <p className="text-white font-medium">Không có tin tuyển dụng</p>
            <p className="text-slate-500 text-sm mt-1">
              {search ? `Không tìm thấy kết quả cho "${search}"` : 'Bắt đầu bằng cách tạo tin mới'}
            </p>
          </div>
          <Link to="/employer/jobs/new" className="btn-primary mt-2">
            <Plus size={15} /> Tạo tin đầu tiên
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map(job => (
            <JobCard
              key={job.id}
              job={job}
              isLoading={loadingId === job.id}
              onPublish={(id) => { setLoadingId(id); publishMutation.mutate(id) }}
              onClose={(id)   => { setLoadingId(id); closeMutation.mutate(id) }}
              onDelete={(id)  => {
                if (window.confirm('Xóa tin nháp này?')) {
                  setLoadingId(id)
                  deleteMutation.mutate(id)
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
