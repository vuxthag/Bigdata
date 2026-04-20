import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Sparkles, CheckCircle2, BrainCircuit, Briefcase } from 'lucide-react'
import { cvsApi } from '../api/cvs'
import { recommendApi } from '../api/recommend'

import PageContainer from '../components/layout/PageContainer'
import SectionCard from '../components/layout/SectionCard'
import CVSelector from './ai/CVSelector'
import SuggestionButton from './ai/SuggestionButton'
import JobResultsList from './ai/JobResultsList'
import CVAnalysisPanel from './ai/CVAnalysisPanel'

export default function RecommendPage() {
  const [searchParams] = useSearchParams()
  const initialCvId = searchParams.get('cv_id') || ''

  const [selectedCvId, setSelectedCvId] = useState(initialCvId)
  const [cvAnalysis, setCvAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('analysis') // 'analysis' | 'jobs'

  const { data: cvList } = useQuery({
    queryKey: ['cvs'],
    queryFn: () => cvsApi.list().then(r => r.data),
  })

  const handleSearch = async () => {
    setError('')
    setLoading(true)
    setCvAnalysis(null)
    setActiveTab('analysis')

    try {
      if (!selectedCvId) {
        setError('Vui lòng chọn CV của bạn trước khi tìm việc.')
        setLoading(false)
        return
      }

      const res = await recommendApi.cvAnalysis({ cv_id: selectedCvId, top_n: 10 })
      setCvAnalysis(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Có lỗi xảy ra')
    } finally {
      setLoading(false)
    }
  }

  const rankedJobs = cvAnalysis?.job_matches || []
  const cvName = cvList?.items?.find(c => c.id === selectedCvId)?.filename || 'CV đã chọn'

  return (
    <PageContainer
      title="AI Gợi ý & Phân tích CV"
      subtitle="AI phân tích CV của bạn, gợi ý việc làm phù hợp và đưa ra lời khuyên cải thiện"
    >
      {/* ── Search Controls ── */}
      <SectionCard>
        <div className="space-y-5">
          <CVSelector
            selectedCvId={selectedCvId}
            onCvChange={setSelectedCvId}
            cvList={cvList}
          />

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-500 text-sm flex items-center gap-2">
              <span>{error}</span>
            </div>
          )}

          <SuggestionButton loading={loading} activeTab="cv" onClick={handleSearch} />
        </div>
      </SectionCard>

      {/* ── Results ── */}
      {cvAnalysis && (
        <div className="space-y-6">
          {/* Header + Tab switcher */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h3 className="text-slate-900 font-semibold flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-brand-400" />
              Kết quả phân tích: <span className="gradient-text">{cvName}</span>
            </h3>
            <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
              <button
                onClick={() => setActiveTab('analysis')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'analysis'
                    ? 'bg-white text-brand-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <BrainCircuit className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
                Phân tích CV
              </button>
              <button
                onClick={() => setActiveTab('jobs')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'jobs'
                    ? 'bg-white text-brand-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <Briefcase className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
                Việc làm phù hợp
                {rankedJobs.length > 0 && (
                  <span className="ml-1.5 bg-brand-100 text-brand-600 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {rankedJobs.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* ── Tab: CV Analysis ── */}
          {activeTab === 'analysis' && (
            <div className="space-y-6">
              <CVAnalysisPanel analysis={cvAnalysis} />

              {/* CTA to switch to jobs */}
              {rankedJobs.length > 0 && (
                <div className="text-center">
                  <button
                    onClick={() => setActiveTab('jobs')}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold
                      bg-gradient-to-r from-brand-600 to-purple-600
                      hover:from-brand-500 hover:to-purple-500
                      text-white transition-all duration-300
                      shadow-lg shadow-brand-600/30 hover:shadow-xl hover:-translate-y-0.5"
                  >
                    <Briefcase className="w-4 h-4" />
                    Xem {rankedJobs.length} công việc phù hợp →
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Job Results ── */}
          {activeTab === 'jobs' && (
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-3">
                <SectionCard className="text-center !p-3">
                  <p className="text-xl font-bold text-slate-900">{rankedJobs.length}</p>
                  <p className="text-slate-500 text-xs mt-0.5">Việc phù hợp</p>
                </SectionCard>
                <SectionCard className="text-center !p-3">
                  <p className="text-xl font-bold text-emerald-500">
                    {rankedJobs.filter(r => (r.final_score || r.similarity_score || 0) >= 0.8).length}
                  </p>
                  <p className="text-slate-500 text-xs mt-0.5">Rất cao (&gt;80%)</p>
                </SectionCard>
                <SectionCard className="text-center !p-3">
                  <p className="text-xl font-bold text-brand-500">
                    {rankedJobs[0]?.final_score != null
                      ? `${(rankedJobs[0].final_score * 100).toFixed(0)}%`
                      : '—'}
                  </p>
                  <p className="text-slate-500 text-xs mt-0.5">Điểm cao nhất</p>
                </SectionCard>
              </div>

              {rankedJobs.length > 0 ? (
                <JobResultsList results={rankedJobs} cvId={selectedCvId} />
              ) : (
                <SectionCard className="text-center py-10">
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                    <CheckCircle2 className="w-6 h-6 text-slate-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-800">Không tìm thấy công việc phù hợp</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Rất tiếc, chưa có công việc nào vượt qua ngưỡng tương thích 40%. Hãy cập nhật thêm kỹ năng vào CV.
                  </p>
                </SectionCard>
              )}
            </div>
          )}
        </div>
      )}
    </PageContainer>
  )
}
