import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { cvsApi } from '../api/cvs'
import { jobsApi } from '../api/jobs'
import { recommendApi } from '../api/recommend'

import PageContainer from '../components/layout/PageContainer'
import SectionCard from '../components/layout/SectionCard'
import SuggestionTabs from './ai/SuggestionTabs'
import CVSelector from './ai/CVSelector'
import ResultSlider from './ai/ResultSlider'
import SuggestionButton from './ai/SuggestionButton'
import JobResultsList from './ai/JobResultsList'
import CandidateResultsList from './ai/CandidateResultsList'

export default function RecommendPage() {
  const [searchParams] = useSearchParams()
  const initialCvId = searchParams.get('cv_id') || ''

  const [activeTab, setActiveTab] = useState(initialCvId ? 'cv' : 'cv')
  const [selectedCvId, setSelectedCvId] = useState(initialCvId)
  const [selectedJobId, setSelectedJobId] = useState('')
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
        if (!jobTitle.trim() && !selectedJobId) { setError('Vui lòng chọn vị trí hoặc nhập chức danh'); setLoading(false); return }
        res = await recommendApi.byTitle({ job_title: jobTitle || selectedJobId, top_n: topN })
      }
      setResults({ ...res.data, tab: activeTab })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (key) => {
    setActiveTab(key)
    setResults(null)
  }

  const handleJobChange = (value) => {
    setSelectedJobId(value)
    if (value) setJobTitle('')
  }

  const handleJobTitleChange = (value) => {
    setJobTitle(value)
    if (value) setSelectedJobId('')
  }

  return (
    <PageContainer
      title="AI Gợi ý"
      subtitle="AI phân tích và gợi ý việc làm phù hợp nhất với bạn"
    >
      {/* ── Search Controls ── */}
      <SectionCard>
        <div className="space-y-5">
          <SuggestionTabs activeTab={activeTab} onTabChange={handleTabChange} />

          <CVSelector
            activeTab={activeTab}
            selectedCvId={selectedCvId}
            onCvChange={setSelectedCvId}
            cvList={cvList}
            selectedJobId={selectedJobId}
            onJobChange={handleJobChange}
            jobList={jobList}
            jobTitle={jobTitle}
            onJobTitleChange={handleJobTitleChange}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />

          <ResultSlider topN={topN} onChange={setTopN} />

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          <SuggestionButton loading={loading} activeTab={activeTab} onClick={handleSearch} />
        </div>
      </SectionCard>

      {/* ── Results ── */}
      {results && (
        <div className="space-y-6">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-400" />
              Kết quả cho: <span className="gradient-text">"{results.query?.slice(0, 40)}"</span>
            </h3>
            <span className="badge-brand text-xs">{results.results?.length || 0} gợi ý</span>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <SectionCard className="text-center">
              <p className="text-2xl font-bold text-white">{results.results?.length || 0}</p>
              <p className="text-slate-500 text-xs mt-1">{activeTab === 'cv' ? 'Việc làm' : 'Ứng viên'}</p>
            </SectionCard>
            <SectionCard className="text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {results.results?.filter(r => r.similarity_score >= 0.8).length || 0}
              </p>
              <p className="text-slate-500 text-xs mt-1">Rất phù hợp</p>
            </SectionCard>
            <SectionCard className="text-center">
              <p className="text-2xl font-bold text-brand-400">
                {results.results?.[0]?.similarity_score ? `${(results.results[0].similarity_score * 100).toFixed(0)}%` : '—'}
              </p>
              <p className="text-slate-500 text-xs mt-1">Điểm cao nhất</p>
            </SectionCard>
          </div>

          {/* Result Cards */}
          {(activeTab === 'cv' || results.tab === 'cv') ? (
            <JobResultsList results={results.results || []} cvId={activeTab === 'cv' ? selectedCvId : null} />
          ) : (
            <CandidateResultsList results={results.results || []} />
          )}
        </div>
      )}
    </PageContainer>
  )
}
