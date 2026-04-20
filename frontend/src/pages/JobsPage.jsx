import React, { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Search, MapPin, Briefcase, Filter, X,
  ChevronLeft, ChevronRight, SlidersHorizontal, Wifi,
  ChevronsLeft, ChevronsRight,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'
import JobCard from '../components/features/jobs/JobCard'

const PER_PAGE = 12

export default function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQ = searchParams.get('q') || ''
  const initialPage = parseInt(searchParams.get('page') || '1', 10)

  /* ── State ─────────────────────────────── */
  const [keyword, setKeyword] = useState(initialQ)
  const [appliedKeyword, setAppliedKeyword] = useState(initialQ)
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(initialPage)

  /* ── Server-side data fetch ────────────── */
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['jobs-list', appliedKeyword, page],
    queryFn: () => jobsApi.list({ page, page_size: PER_PAGE, search: appliedKeyword || undefined }).then(r => r.data),
    keepPreviousData: true,
  })

  const jobs = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  /* ── Handlers ──────────────────────────── */
  const goToPage = useCallback((p) => {
    const next = Math.max(1, Math.min(p, totalPages))
    setPage(next)
    const params = {}
    if (appliedKeyword) params.q = appliedKeyword
    if (next > 1) params.page = next
    setSearchParams(params)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [totalPages, appliedKeyword, setSearchParams])

  const handleSearch = () => {
    setAppliedKeyword(keyword)
    setPage(1)
    const params = {}
    if (keyword) params.q = keyword
    setSearchParams(params)
  }

  const clearSearch = () => {
    setKeyword('')
    setAppliedKeyword('')
    setPage(1)
    setSearchParams({})
  }

  /* ── Pagination range ──────────────────── */
  const getPageNumbers = () => {
    const maxVisible = 7
    if (totalPages <= maxVisible) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }
    const pages = []
    pages.push(1)
    let start = Math.max(2, page - 1)
    let end = Math.min(totalPages - 1, page + 1)
    if (page <= 3) { start = 2; end = 5 }
    if (page >= totalPages - 2) { start = totalPages - 4; end = totalPages - 1 }
    if (start > 2) pages.push('...')
    for (let i = start; i <= end; i++) pages.push(i)
    if (end < totalPages - 1) pages.push('...')
    pages.push(totalPages)
    return pages
  }

  return (
    <div className="section-container py-10 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="section-heading">Tìm kiếm việc làm</h1>
        <p className="section-subheading">
          Khám phá <span className="font-semibold text-brand-500">{total.toLocaleString()}</span> cơ hội phù hợp với năng lực của bạn
        </p>
      </div>

      {/* Search bar */}
      <div className="glass-card p-3 flex flex-col sm:flex-row gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            className="search-input pl-10"
            placeholder="Chức danh, kỹ năng, từ khóa..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button onClick={handleSearch} className="btn-accent py-3 px-6">
          <Search className="w-4 h-4" />
          Tìm kiếm
        </button>
      </div>

      {/* Applied filter indicator */}
      {appliedKeyword && (
        <div className="flex items-center gap-2 mb-6">
          <span className="text-slate-500 text-sm">Kết quả cho:</span>
          <span className="badge-brand">{appliedKeyword}</span>
          <button onClick={clearSearch} className="text-slate-500 hover:text-red-400 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
          <span className="text-slate-600 text-xs ml-2">{total.toLocaleString()} kết quả</span>
        </div>
      )}

      {/* ── Jobs Grid ──────────────────────── */}
      <div className="min-w-0">
        {/* Results count + page info */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-slate-500 text-sm">
            {total > 0 ? (
              <>Hiển thị <span className="font-medium text-slate-700">{(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)}</span> / {total.toLocaleString()} việc làm</>
            ) : (
              '0 việc làm'
            )}
          </p>
          <p className="text-slate-600 text-xs">Trang {page}/{totalPages}</p>
        </div>

        {/* Loading / Content */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array(PER_PAGE).fill(0).map((_, i) => (
              <div key={i} className="glass-card p-5 animate-pulse h-44 bg-slate-100" />
            ))}
          </div>
        ) : jobs.length > 0 ? (
          <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 transition-opacity duration-200 ${isFetching ? 'opacity-60' : ''}`}>
            {jobs.map(job => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        ) : (
          <div className="glass-card p-12 text-center">
            <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Không tìm thấy việc làm phù hợp</p>
          </div>
        )}

        {/* ── Pagination ─────────────────────── */}
        {totalPages > 1 && (
          <div className="flex flex-col items-center gap-4 mt-8">
            {/* Page buttons */}
            <div className="flex items-center gap-1.5">
              {/* First page */}
              <button
                onClick={() => goToPage(1)}
                disabled={page === 1}
                className="btn-secondary py-2 px-2 disabled:opacity-30"
                title="Trang đầu"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>

              {/* Prev */}
              <button
                onClick={() => goToPage(page - 1)}
                disabled={page === 1}
                className="btn-secondary py-2 px-2 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {/* Page numbers */}
              {getPageNumbers().map((p, i) =>
                p === '...' ? (
                  <span key={`dots-${i}`} className="w-9 h-9 flex items-center justify-center text-slate-400 text-sm">…</span>
                ) : (
                  <button
                    key={p}
                    onClick={() => goToPage(p)}
                    className={`w-9 h-9 rounded-lg text-sm font-medium transition-all ${
                      page === p
                        ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
                        : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {p}
                  </button>
                )
              )}

              {/* Next */}
              <button
                onClick={() => goToPage(page + 1)}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-2 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>

              {/* Last page */}
              <button
                onClick={() => goToPage(totalPages)}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-2 disabled:opacity-30"
                title="Trang cuối"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>

            {/* Jump to page */}
            <div className="flex items-center gap-2">
              <span className="text-slate-500 text-xs">Đi đến trang:</span>
              <input
                type="number"
                min={1}
                max={totalPages}
                className="w-16 text-center text-sm border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const v = parseInt(e.target.value, 10)
                    if (v >= 1 && v <= totalPages) goToPage(v)
                  }
                }}
                placeholder={String(page)}
              />
              <span className="text-slate-400 text-xs">/ {totalPages}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
