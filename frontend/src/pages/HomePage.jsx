import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, MapPin, Briefcase, ArrowRight, Star,
  Code2, Brain, TrendingUp, DollarSign, Users, PenTool,
  BarChart3, Cpu, FileText, Sparkles, Building2, Zap,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'
import { analyticsApi } from '../api/analytics'
import useAuthStore from '../store/authStore'

const CATEGORIES = [
  { icon: Code2, label: 'IT / Software', color: 'from-blue-500/20 to-blue-600/10 border-slate-200lue-500/20 text-blue-400' },
  { icon: Brain, label: 'Data / AI', color: 'from-purple-500/20 to-purple-600/10 border-purple-500/20 text-purple-400' },
  { icon: TrendingUp, label: 'Marketing', color: 'from-pink-500/20 to-pink-600/10 border-pink-500/20 text-pink-400' },
  { icon: DollarSign, label: 'Finance', color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/20 text-emerald-400' },
  { icon: Users, label: 'Human Resources', color: 'from-amber-500/20 to-amber-600/10 border-slate-200mber-500/20 text-amber-400' },
  { icon: BarChart3, label: 'Sales', color: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/20 text-cyan-400' },
  { icon: PenTool, label: 'Design', color: 'from-rose-500/20 to-rose-600/10 border-slate-200ose-500/20 text-rose-400' },
  { icon: Cpu, label: 'Engineering', color: 'from-indigo-500/20 to-indigo-600/10 border-indigo-500/20 text-indigo-400' },
]

function SimilarityBadge({ score }) {
  if (score >= 0.8) return <span className="badge-green text-xs">🟢 {(score * 100).toFixed(0)}% phù hợp</span>
  if (score >= 0.6) return <span className="badge-yellow text-xs">🟡 {(score * 100).toFixed(0)}% phù hợp</span>
  return <span className="badge-gray text-xs">⚪ {(score * 100).toFixed(0)}%</span>
}

function FeaturedJobCard({ job }) {
  return (
    <div className="glass-card p-5 hover:border-slate-200rand-500/20 hover:-translate-y-1 transition-all duration-300 group">
      <div className="flex items-start gap-4">
        {/* Company avatar */}
        <div className="w-12 h-12 rounded-xl bg-slate-50radient-to-br from-brand-500/20 to-purple-500/20 border border-slate-200rand-500/20 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-6 h-6 text-brand-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-slate-900 font-semibold text-sm group-hover:text-brand-400 transition-colors truncate">
            {job.position_title}
          </h3>
          <p className="text-slate-500 text-xs mt-0.5">JobMatch AI</p>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="tag-fulltime">Full-time</span>
            <span className="tag">
              <MapPin className="w-3 h-3 mr-0.5" />
              Hà Nội
            </span>
          </div>
        </div>
      </div>
      <p className="text-slate-500 text-xs mt-3 line-clamp-2 leading-relaxed">
        {job.description?.substring(0, 120) || 'Mô tả công việc sẽ xuất hiện ở đây...'}
      </p>
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-200">
        <span className="text-slate-600 text-xs">Đăng gần đây</span>
        <Link to="/recommend" className="text-brand-400 text-xs font-medium hover:text-brand-300 flex items-center gap-1 group-hover:gap-2 transition-all">
          Xem chi tiết <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [keyword, setKeyword] = useState('')

  const { data: jobsData } = useQuery({
    queryKey: ['featured-jobs'],
    queryFn: () => jobsApi.list({ page_size: 6 }).then(r => r.data),
  })

  const { data: dashboardData } = useQuery({
    queryKey: ['home-stats'],
    queryFn: () => analyticsApi.dashboard().then(r => r.data).catch(() => null),
    enabled: isAuthenticated,
  })

  const jobs = jobsData?.items || []

  const handleSearch = () => {
    navigate(`/jobs?q=${encodeURIComponent(keyword)}`)
  }

  return (
    <div className="animate-fade-in">
      {/* ════════════════════════════════════════════
          HERO SECTION
          ════════════════════════════════════════════ */}
      <section className="relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-slate-50rand-600/15 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-purple-600/15 rounded-full blur-[120px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-slate-50ccent-500/8 rounded-full blur-[100px]" />
        </div>

        <div className="section-container relative z-10 py-20 md:py-28">
          <div className="max-w-3xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-50rand-500/10 border border-slate-200rand-500/20 mb-6 animate-slide-down">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-brand-400 text-xs font-medium">Powered by Sentence-BERT + pgvector</span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-slate-900 leading-tight animate-slide-up">
              Tìm việc làm mơ ước
              <br />
              <span className="gradient-text">với sức mạnh AI</span>
            </h1>

            <p className="text-slate-600 text-base sm:text-lg mt-5 max-w-xl mx-auto leading-relaxed animate-slide-up">
              JobMatch AI phân tích CV của bạn và gợi ý vị trí phù hợp nhất bằng công nghệ embedding ngữ nghĩa tiên tiến
            </p>

            {/* ── Search bar ──────────────────── */}
            <div className="mt-8 glass-card p-3 flex flex-col sm:flex-row gap-2 max-w-2xl mx-auto animate-slide-up">
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
              <div className="relative flex-1 hidden sm:block">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  className="search-input pl-10"
                  placeholder="Địa điểm..."
                />
              </div>
              <button onClick={handleSearch} className="btn-accent py-3.5 px-6">
                <Search className="w-4 h-4" />
                Tìm kiếm
              </button>
            </div>

            {/* Popular searches */}
            <div className="mt-4 flex items-center justify-center gap-2 flex-wrap text-xs text-slate-500">
              <span>Phổ biến:</span>
              {['Data Scientist', 'React Developer', 'DevOps', 'Product Manager'].map(t => (
                <button key={t} onClick={() => { setKeyword(t); navigate(`/jobs?q=${encodeURIComponent(t)}`) }}
                  className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-50rand-500/10 hover:text-brand-400 transition-colors cursor-pointer">
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          JOB CATEGORIES
          ════════════════════════════════════════════ */}
      <section className="section-container py-16">
        <div className="text-center mb-10">
          <h2 className="section-heading">Khám phá theo danh mục</h2>
          <p className="section-subheading">Tìm vị trí phù hợp với chuyên ngành của bạn</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {CATEGORIES.map(({ icon: Icon, label, color }) => (
            <Link
              to={`/jobs?q=${encodeURIComponent(label.split('/')[0].trim())}`}
              key={label}
              className={`glass-card p-5 flex flex-col items-center gap-3 cursor-pointer hover:-translate-y-1 transition-all duration-300 bg-slate-50radient-to-br ${color} border`}
            >
              <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
                <Icon className="w-6 h-6" />
              </div>
              <span className="text-slate-900 text-sm font-medium text-center">{label}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* ════════════════════════════════════════════
          FEATURED JOBS
          ════════════════════════════════════════════ */}
      <section className="section-container py-16">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="section-heading">Việc làm nổi bật</h2>
            <p className="section-subheading">Những vị trí mới nhất trên nền tảng</p>
          </div>
          <Link to="/jobs" className="btn-ghost text-xs hidden sm:flex">
            Xem tất cả <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {jobs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {jobs.map(job => (
              <FeaturedJobCard key={job.id} job={job} />
            ))}
          </div>
        ) : (
          <div className="glass-card p-12 text-center">
            <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Chưa có việc làm nào. Hãy đăng tin tuyển dụng!</p>
            <Link to="/upload-job" className="btn-primary mt-4 text-xs">Đăng tin ngay</Link>
          </div>
        )}

        <div className="text-center mt-6 sm:hidden">
          <Link to="/jobs" className="btn-ghost text-xs">Xem tất cả <ArrowRight className="w-3.5 h-3.5" /></Link>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          AI RECOMMENDATION PREVIEW
          ════════════════════════════════════════════ */}
      <section className="py-16 relative">
        <div className="absolute inset-0 bg-slate-50radient-to-r from-brand-600/5 via-purple-600/5 to-brand-600/5 pointer-events-none" />
        <div className="section-container relative z-10">
          <div className="flex flex-col md:flex-row items-center gap-10">
            <div className="flex-1 space-y-5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-50rand-500/10 border border-slate-200rand-500/20">
                <Zap className="w-3.5 h-3.5 text-brand-400" />
                <span className="text-brand-400 text-xs font-medium">AI-Powered Matching</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 leading-tight">
                Gợi ý việc làm
                <br />
                <span className="gradient-text">cá nhân hóa cho bạn</span>
              </h2>
              <p className="text-slate-500 text-sm leading-relaxed">
                Upload CV của bạn — AI sẽ phân tích nội dung, tạo embedding ngữ nghĩa và so khớp với hàng nghìn
                vị trí tuyển dụng bằng cosine similarity qua pgvector. Kết quả chính xác đến từng kỹ năng.
              </p>
              <div className="flex gap-3">
                <Link to={isAuthenticated ? '/upload' : '/register'} className="btn-primary text-sm">
                  <FileText className="w-4 h-4" />
                  {isAuthenticated ? 'Upload CV ngay' : 'Đăng ký để bắt đầu'}
                </Link>
                <Link to="/recommend" className="btn-secondary text-sm">
                  <Search className="w-4 h-4" />
                  Tìm việc AI
                </Link>
              </div>
            </div>
            <div className="flex-1 w-full max-w-md">
              {/* AI Feature cards */}
              <div className="space-y-3">
                {[
                  { icon: Brain, title: 'Sentence-BERT Embeddings', desc: 'Biểu diễn ngữ nghĩa 384 chiều cho mỗi CV & JD' },
                  { icon: Cpu, title: 'pgvector Cosine Similarity', desc: 'Tìm kiếm tương đồng siêu nhanh trên PostgreSQL' },
                  { icon: Sparkles, title: 'Continual Learning', desc: 'AI tự cải thiện theo phản hồi của người dùng' },
                ].map(({ icon: Icon, title, desc }) => (
                  <div key={title} className="glass-card p-4 flex items-start gap-3 hover:border-slate-200rand-500/20 transition-colors">
                    <div className="w-9 h-9 rounded-lg bg-slate-50rand-500/15 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-brand-400" />
                    </div>
                    <div>
                      <h4 className="text-slate-900 text-sm font-semibold">{title}</h4>
                      <p className="text-slate-600 text-xs mt-0.5">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>



      {/* ════════════════════════════════════════════
          CTA
          ════════════════════════════════════════════ */}
      <section className="section-container py-16">
        <div className="glass-card p-10 md:p-14 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-slate-50radient-to-r from-brand-600/10 via-purple-600/10 to-brand-600/10 pointer-events-none" />
          <div className="relative z-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-3">
              Sẵn sàng tìm công việc tiếp theo?
            </h2>
            <p className="text-slate-600 text-sm max-w-md mx-auto mb-6">
              Tạo tài khoản miễn phí, upload CV và để AI tìm vị trí phù hợp nhất dành cho bạn.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link to={isAuthenticated ? '/upload' : '/register'} className="btn-accent">
                <Sparkles className="w-4 h-4" />
                {isAuthenticated ? 'Upload CV ngay' : 'Bắt đầu miễn phí'}
              </Link>
              <Link to="/jobs" className="btn-secondary">
                Xem việc làm
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
