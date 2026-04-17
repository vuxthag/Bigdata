import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Sparkles, CheckCircle2 } from 'lucide-react'
import { cvsApi } from '../api/cvs'
import { recommendApi } from '../api/recommend'

import PageContainer from '../components/layout/PageContainer'
import SectionCard from '../components/layout/SectionCard'
import CVSelector from './ai/CVSelector'
import SuggestionButton from './ai/SuggestionButton'
import JobResultsList from './ai/JobResultsList'

export default function RecommendPage() {
  const [searchParams] = useSearchParams()
  const initialCvId = searchParams.get('cv_id') || ''

  const [selectedCvId, setSelectedCvId] = useState(initialCvId)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: cvList } = useQuery({
    queryKey: ['cvs'],
    queryFn: () => cvsApi.list().then(r => r.data),
  })

  const handleSearch = async () => {
    setError('')
    setLoading(true)
    setResults(null)
    
    try {
      if (!selectedCvId) { 
        setError('Vui lòng chọn CV của bạn trước khi tìm việc.'); 
        setLoading(false); 
        return; 
      }
      
      const res = await recommendApi.byCV({ cv_id: selectedCvId, top_n: 5 })
      setResults(res.data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageContainer
      title="AI Gợi ý"
      subtitle="AI phân tích CV của bạn và gợi ý TOP 5 việc làm phù hợp nhất (độ tương thích > 50%)"
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
      {results && results.results && (
        <div className="space-y-6">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-slate-900 font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-400" />
              Kết quả cho CV: <span className="gradient-text">{cvList?.items?.find(c => c.id === selectedCvId)?.filename || "CV đã chọn"}</span>
            </h3>
            <span className="badge-brand text-xs">{results.results.length} công việc</span>
          </div>

          {results.results.length > 0 ? (
            <>
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <SectionCard className="text-center">
                  <p className="text-2xl font-bold text-slate-900">{results.results.length}</p>
                  <p className="text-slate-500 text-xs mt-1">Việc làm phù hợp</p>
                </SectionCard>
                <SectionCard className="text-center">
                  <p className="text-2xl font-bold text-emerald-500">
                    {results.results.filter(r => r.similarity_score >= 0.8).length}
                  </p>
                  <p className="text-slate-500 text-xs mt-1">Độ phù hợp rất cao ({'>'}80%)</p>
                </SectionCard>
                <SectionCard className="text-center">
                  <p className="text-2xl font-bold text-brand-500">
                    {results.results[0]?.similarity_score ? `${(results.results[0].similarity_score * 100).toFixed(0)}%` : '—'}
                  </p>
                  <p className="text-slate-500 text-xs mt-1">Điểm cao nhất</p>
                </SectionCard>
              </div>

              {/* Result Cards */}
              <JobResultsList results={results.results} cvId={selectedCvId} />
            </>
          ) : (
            <SectionCard className="text-center py-10">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="w-6 h-6 text-slate-400" />
              </div>
              <h3 className="text-sm font-semibold text-slate-800">Không tìm thấy công việc phù hợp</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Rất tiếc, chưa có công việc nào trong hệ thống vượt qua mức độ tương thích 50% so với kỹ năng trong CV của bạn. Hãy thử cập nhật thêm kỹ năng vào CV.
              </p>
            </SectionCard>
          )}
        </div>
      )}
    </PageContainer>
  )
}
