import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Search, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { cvsApi } from '../api/cvs'
import { jobsApi } from '../api/jobs'
import { recommendApi } from '../api/recommend'

function SimilarityBadge({ score }) {
  if (score >= 0.8) return <span className="badge-green">🟢 Rất phù hợp {(score * 100).toFixed(0)}%</span>
  if (score >= 0.6) return <span className="badge-yellow">🟡 Phù hợp {(score * 100).toFixed(0)}%</span>
  return <span className="badge-gray">⚪ Có thể phù hợp {(score * 100).toFixed(0)}%</span>
}

function JobCard({ job, rank, cvId }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const feedbackMutation = useMutation({
    mutationFn: (action) => recommendApi.feedback({ job_id: job.job_id, action, cv_id: cvId, similarity_score: job.similarity_score }),
    onSuccess: (_, action) => setFeedback(action),
  })

  return (
    <div className="glass-card p-5 hover:border-brand-500/20 transition-all duration-200 animate-slide-up">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400 text-xs font-bold flex-shrink-0">#{rank}</span>
          <h3 className="text-white font-semibold text-sm leading-snug">{job.position_title}</h3>
        </div>
        <SimilarityBadge score={job.similarity_score} />
      </div>

      <p className="text-slate-400 text-sm leading-relaxed">
        {expanded ? job.description_preview : job.description_preview?.slice(0, 150) + (job.description_preview?.length > 150 ? '...' : '')}
      </p>
      {job.description_preview?.length > 150 && (
        <button onClick={() => setExpanded(!expanded)} className="text-brand-400 text-xs mt-1 flex items-center gap-1 hover:text-brand-300">
          {expanded ? <><ChevronUp className="w-3 h-3" /> Thu gọn</> : <><ChevronDown className="w-3 h-3" /> Xem thêm</>}
        </button>
      )}

      {/* Feedback buttons */}
      <div className="flex items-center gap-2 mt-4">
        {feedback ? (
          <span className="text-emerald-400 text-xs flex items-center gap-1">✓ Đã ghi nhận — <span className="capitalize">{feedback}</span></span>
        ) : (
          <>
            <button onClick={() => feedbackMutation.mutate('applied')} disabled={feedbackMutation.isPending}
              className="btn-primary py-2 px-3 text-xs from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 shadow-emerald-600/20">
              💼 Ứng tuyển
            </button>
            <button onClick={() => feedbackMutation.mutate('saved')} disabled={feedbackMutation.isPending}
              className="btn-secondary py-2 px-3 text-xs">
              🔖 Lưu lại
            </button>
            <button onClick={() => feedbackMutation.mutate('skipped')} disabled={feedbackMutation.isPending}
              className="p-2 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-colors text-xs">
              ✕ Bỏ qua
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default function RecommendPage() {
  const [searchParams] = useSearchParams()
  const initialCvId = searchParams.get('cv_id') || ''

  const [activeTab, setActiveTab] = useState(initialCvId ? 'cv' : 'title')
  const [selectedCvId, setSelectedCvId] = useState(initialCvId)
  const [jobTitle, setJobTitle] = useState('')
  const [topN, setTopN] = useState(5)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: cvList } = useQuery({
    queryKey: ['cvs'],
    queryFn: () => cvsApi.list().then(r => r.data),
  })
  const { data: jobList } = useQuery({
    queryKey: ['jobs-all'],
    queryFn: () => jobsApi.list({ page_size: 100 }).then(r => r.data),
  })

  const handleSearch = async () => {
    setError('')
    setLoading(true)
    setResults(null)
    try {
      let res
      if (activeTab === 'cv') {
        if (!selectedCvId) { setError('Vui lòng chọn CV'); setLoading(false); return }
        res = await recommendApi.byCV({ cv_id: selectedCvId, top_n: topN })
      } else {
        if (!jobTitle.trim()) { setError('Vui lòng nhập chức danh'); setLoading(false); return }
        res = await recommendApi.byTitle({ job_title: jobTitle, top_n: topN })
      }
      setResults(res.data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Gợi ý việc làm</h2>
        <p className="text-slate-400 text-sm mt-1">AI phân tích và gợi ý việc làm phù hợp nhất với bạn</p>
      </div>

      {/* Tabs */}
      <div className="glass-card p-6 space-y-5">
        <div className="flex gap-2 p-1 bg-dark-700/50 rounded-xl">
          {[['cv', '📄 Theo CV của bạn'], ['title', '🔤 Theo chức danh']].map(([key, label]) => (
            <button key={key} onClick={() => setActiveTab(key)}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200
                ${activeTab === key ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20' : 'text-slate-400 hover:text-white'}`}>
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'cv' ? (
          <div>
            <label className="field-label">Chọn CV</label>
            <select className="input-field" value={selectedCvId} onChange={e => setSelectedCvId(e.target.value)}>
              <option value="">-- Chọn CV --</option>
              {cvList?.items?.map(cv => (
                <option key={cv.id} value={cv.id}>{cv.filename}</option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label className="field-label">Tên chức danh</label>
            <input className="input-field" placeholder="VD: Data Scientist, Software Engineer..."
              value={jobTitle} onChange={e => setJobTitle(e.target.value)}
              list="job-titles-list"
              onKeyDown={e => e.key === 'Enter' && handleSearch()} />
            <datalist id="job-titles-list">
              {jobList?.items?.slice(0, 50).map(j => <option key={j.id} value={j.position_title} />)}
            </datalist>
          </div>
        )}

        {/* Top N slider */}
        <div>
          <label className="field-label">Số kết quả: <span className="text-brand-400">{topN}</span></label>
          <input type="range" min={3} max={15} value={topN} onChange={e => setTopN(Number(e.target.value))}
            className="w-full accent-brand-500" />
        </div>

        {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm">{error}</div>}

        <button onClick={handleSearch} className="btn-primary" disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          {loading ? 'Đang tìm kiếm...' : 'Tìm việc phù hợp'}
        </button>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold">
              Kết quả cho: <span className="gradient-text">"{results.query.slice(0, 40)}"</span>
            </h3>
            <span className="badge-brand text-xs">{results.results.length} gợi ý</span>
          </div>
          {results.results.map((job, i) => (
            <JobCard key={job.job_id} job={job} rank={i + 1} cvId={activeTab === 'cv' ? selectedCvId : null} />
          ))}
        </div>
      )}
    </div>
  )
}
