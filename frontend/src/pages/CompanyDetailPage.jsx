import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Building2, MapPin, Users, Briefcase, Globe, ArrowLeft, ExternalLink,
} from 'lucide-react'
import { jobsApi } from '../api/jobs'
import JobCard from '../components/JobCard'

/* ── Mock company data ──────────────────────── */
function getCompanyData(companyId) {
  return {
    id: companyId,
    name: decodeURIComponent(companyId).replace(/-/g, ' '),
    industry: 'Công nghệ thông tin',
    description: 'Chúng tôi là một công ty công nghệ hàng đầu, chuyên phát triển các giải pháp AI và Machine Learning tiên tiến. Với đội ngũ kỹ sư tài năng, chúng tôi cam kết mang đến những sản phẩm công nghệ tốt nhất cho khách hàng.',
    founded: '2020',
    size: '50-200 nhân viên',
    location: 'TP. Hồ Chí Minh, Việt Nam',
    website: 'https://example.com',
    benefits: ['Work from home', 'Bảo hiểm sức khỏe', '13th month salary', 'Đào tạo & phát triển', 'Team building'],
  }
}

export default function CompanyDetailPage() {
  const { companyId } = useParams()
  const company = getCompanyData(companyId)

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['company-jobs', companyId],
    queryFn: () => jobsApi.list({ page_size: 50 }).then(r => r.data),
  })

  // Filter jobs that match the company (mock: just show first 6)
  const companyJobs = (jobsData?.items || []).slice(0, 6)

  return (
    <div className="section-container py-10 animate-fade-in">
      {/* Back */}
      <Link to="/companies" className="inline-flex items-center gap-1.5 text-slate-400 hover:text-white text-sm mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Quay lại danh sách công ty
      </Link>

      {/* ── Company Header ─────────────────── */}
      <div className="glass-card p-6 sm:p-8 mb-8">
        <div className="flex flex-col sm:flex-row items-start gap-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
            <Building2 className="w-10 h-10 text-brand-400" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white">{company.name}</h1>
            <p className="text-brand-400 font-medium mt-1">{company.industry}</p>
            <div className="flex items-center gap-4 mt-3 flex-wrap text-sm text-slate-400">
              <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {company.location}</span>
              <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {company.size}</span>
              <span className="flex items-center gap-1"><Briefcase className="w-3.5 h-3.5" /> {companyJobs.length} vị trí mở</span>
            </div>
          </div>
          <a href={company.website} target="_blank" rel="noreferrer" className="btn-secondary">
            <Globe className="w-4 h-4" /> Website <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* ── Content Grid ──────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: About + Benefits */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-card p-6">
            <h3 className="text-white font-semibold mb-3">Về công ty</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{company.description}</p>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-white font-semibold mb-3">Thông tin</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between text-slate-400">
                <span>Ngành nghề</span>
                <span className="text-white">{company.industry}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Quy mô</span>
                <span className="text-white">{company.size}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Thành lập</span>
                <span className="text-white">{company.founded}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Địa điểm</span>
                <span className="text-white">{company.location}</span>
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-white font-semibold mb-3">Phúc lợi</h3>
            <div className="flex flex-wrap gap-2">
              {company.benefits.map(b => (
                <span key={b} className="badge-brand text-xs">{b}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Open positions */}
        <div className="lg:col-span-2">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-brand-400" />
            Vị trí đang tuyển ({companyJobs.length})
          </h3>
          {isLoading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="glass-card p-5 animate-pulse h-32 bg-dark-700/50" />)}
            </div>
          ) : companyJobs.length > 0 ? (
            <div className="grid grid-cols-1 gap-4">
              {companyJobs.map(job => (
                <JobCard key={job.id} job={{ ...job, company_name: company.name }} />
              ))}
            </div>
          ) : (
            <div className="glass-card p-12 text-center">
              <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Chưa có vị trí nào đang tuyển</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
