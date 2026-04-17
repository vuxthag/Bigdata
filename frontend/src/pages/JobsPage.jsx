import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Search, MapPin, Briefcase, Filter, X,
  ChevronLeft, ChevronRight, SlidersHorizontal, Wifi,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'
import JobCard from '../components/features/jobs/JobCard'

/* ── Helpers ───────────────────────────────── */
function getSavedJobs() {
  try { return JSON.parse(localStorage.getItem('savedJobs') || '[]') } catch { return [] }
}
function setSavedJobs(arr) { localStorage.setItem('savedJobs', JSON.stringify(arr)) }

const JOB_TYPES = ['Tất cả', 'Full-time', 'Part-time', 'Intern', 'Remote']
const SORT_OPTIONS = [
  { value: 'newest', label: 'Mới nhất' },
  { value: 'salary', label: 'Lương cao nhất' },
  { value: 'relevance', label: 'Phù hợp nhất' },
]
const PER_PAGE = 12

export default function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQ = searchParams.get('q') || ''

  /* ── Filter state ─────────────────────── */
  const [keyword, setKeyword] = useState(initialQ)
  const [appliedKeyword, setAppliedKeyword] = useState(initialQ)
  const [locFilter, setLocFilter] = useState('')
  const [jobType, setJobType] = useState('Tất cả')
  const [sortBy, setSortBy] = useState('newest')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)
  const [savedJobs, _setSaved] = useState(getSavedJobs)

  /* ── Data ──────────────────────────────── */
  const { data, isLoading } = useQuery({
    queryKey: ['jobs-list', appliedKeyword],
    queryFn: () => jobsApi.list({ page_size: 100 }).then(r => r.data),
  })

  const jobs = data?.items || []

  /* ── Client-side filtering ─────────────── */
  const filtered = useMemo(() => {
    let list = [...jobs]

    // Keyword
    if (appliedKeyword) {
      const kw = appliedKeyword.toLowerCase()
      list = list.filter(j =>
        j.position_title?.toLowerCase().includes(kw) ||
        j.description?.toLowerCase().includes(kw)
      )
    }

    // Location
    if (locFilter) {
      const loc = locFilter.toLowerCase()
      list = list.filter(j => j.location?.toLowerCase().includes(loc))
    }

    // Job type
    if (jobType !== 'Tất cả') {
      if (jobType === 'Remote') {
        list = list.filter(j => j.job_type?.toLowerCase().includes('remote'))
      } else {
        list = list.filter(j => j.job_type?.toLowerCase().includes(jobType.toLowerCase()))
      }
    }

    // Remote only
    if (remoteOnly) {
      list = list.filter(j =>
        j.job_type?.toLowerCase().includes('remote') ||
        j.description?.toLowerCase().includes('remote')
      )
    }

    // Sort
    if (sortBy === 'salary') {
      list.sort((a, b) => (b.salary_num || 0) - (a.salary_num || 0))
    }

    return list
  }, [jobs, appliedKeyword, locFilter, jobType, sortBy, remoteOnly])

  /* ── Pagination ────────────────────────── */
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const paginated = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE)

  const handleSearch = () => {
    setAppliedKeyword(keyword)
    setSearchParams(keyword ? { q: keyword } : {})
    setPage(1)
  }

  const handleSave = (jobId) => {
    const list = getSavedJobs()
    list.push(jobId)
    setSavedJobs(list)
    _setSaved([...list])
  }
  const handleRemove = (jobId) => {
    const list = getSavedJobs().filter(id => id !== jobId)
    setSavedJobs(list)
    _setSaved([...list])
  }

  return (
    <div className="section-container py-10 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="section-heading">Tìm kiếm việc làm</h1>
        <p className="section-subheading">Khám phá hàng trăm cơ hội phù hợp với năng lực của bạn</p>
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
        <div className="relative sm:w-48">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            className="search-input pl-10"
            placeholder="Địa điểm..."
            value={locFilter}
            onChange={(e) => setLocFilter(e.target.value)}
          />
        </div>
        <button onClick={handleSearch} className="btn-accent py-3 px-6">
          <Search className="w-4 h-4" />
          Tìm kiếm
        </button>
        <button onClick={() => setShowFilters(!showFilters)} className="btn-secondary py-3 px-4 lg:hidden">
          <Filter className="w-4 h-4" />
        </button>
      </div>

      {/* Applied filter indicator */}
      {appliedKeyword && (
        <div className="flex items-center gap-2 mb-6">
          <span className="text-slate-500 text-sm">Kết quả cho:</span>
          <span className="badge-brand">{appliedKeyword}</span>
          <button onClick={() => { setKeyword(''); setAppliedKeyword(''); setSearchParams({}); setPage(1) }}
            className="text-slate-500 hover:text-red-400 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
          <span className="text-slate-600 text-xs ml-2">{filtered.length} kết quả</span>
        </div>
      )}

      {/* Main content: Sidebar + Jobs grid */}
      <div className="flex gap-6">
        {/* ── Filters Sidebar ─────────────── */}
        <aside className={`w-64 flex-shrink-0 space-y-5 ${showFilters ? 'block' : 'hidden lg:block'}`}>
          <div className="glass-card p-5 space-y-5 sticky top-24">
            <h3 className="text-slate-900 font-semibold text-sm flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-brand-400" />
              Bộ lọc
            </h3>

            {/* Job Type */}
            <div>
              <label className="field-label">Loại công việc</label>
              <div className="space-y-1.5">
                {JOB_TYPES.map(t => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="radio" name="jobType" checked={jobType === t}
                      onChange={() => { setJobType(t); setPage(1) }}
                      className="accent-brand-500"
                    />
                    <span className="text-slate-500 text-sm group-hover:text-slate-900 transition-colors">{t}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Remote toggle */}
            <div className="flex items-center justify-between">
              <span className="text-slate-500 text-sm flex items-center gap-1.5">
                <Wifi className="w-3.5 h-3.5" /> Remote
              </span>
              <button
                onClick={() => { setRemoteOnly(!remoteOnly); setPage(1) }}
                className={`w-10 h-5 rounded-full transition-colors relative ${remoteOnly ? 'bg-slate-50rand-500' : 'bg-dark-600'}`}
              >
                <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${remoteOnly ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
            </div>

            {/* Sort */}
            <div>
              <label className="field-label">Sắp xếp theo</label>
              <select
                className="input-field text-sm"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                {SORT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Reset */}
            <button
              onClick={() => { setJobType('Tất cả'); setRemoteOnly(false); setSortBy('newest'); setLocFilter(''); setPage(1) }}
              className="btn-ghost text-xs w-full justify-center"
            >
              Xóa bộ lọc
            </button>
          </div>
        </aside>

        {/* ── Jobs Grid ──────────────────── */}
        <div className="flex-1 min-w-0">
          {/* Results count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-slate-500 text-sm">{filtered.length} việc làm</p>
            <p className="text-slate-600 text-xs">Trang {page}/{totalPages}</p>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array(4).fill(0).map((_, i) => (
                <div key={i} className="glass-card p-5 animate-pulse h-40 bg-slate-1000" />
              ))}
            </div>
          ) : paginated.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {paginated.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSaved={savedJobs.includes(job.id)}
                  onSave={handleSave}
                  onRemove={handleRemove}
                />
              ))}
            </div>
          ) : (
            <div className="glass-card p-12 text-center">
              <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Không tìm thấy việc làm phù hợp</p>
            </div>
          )}

          {/* ── Pagination ─────────────────── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="btn-secondary py-2 px-3 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let p
                if (totalPages <= 5) p = i + 1
                else if (page <= 3) p = i + 1
                else if (page >= totalPages - 2) p = totalPages - 4 + i
                else p = page - 2 + i
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-9 h-9 rounded-lg text-sm font-medium transition-all ${
                      page === p
                        ? 'bg-slate-50rand-600 text-slate-900 shadow-lg shadow-brand-600/20'
                        : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {p}
                  </button>
                )
              })}

              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-3 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
