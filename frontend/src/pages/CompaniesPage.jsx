import React from 'react'
import { Link } from 'react-router-dom'
import { Building2, MapPin, Briefcase, ArrowRight } from 'lucide-react'

const SAMPLE_COMPANIES = [
  { name: 'Tech Corp', jobs: 12, field: 'IT / Software' },
  { name: 'DataVN', jobs: 8, field: 'Data / AI' },
  { name: 'Creative Studio', jobs: 5, field: 'Design' },
  { name: 'Finance Plus', jobs: 10, field: 'Finance' },
  { name: 'Marketing Pro', jobs: 7, field: 'Marketing' },
  { name: 'DevOps Labs', jobs: 6, field: 'Engineering' },
]

export default function CompaniesPage() {
  return (
    <div className="section-container py-10 animate-fade-in">
      <div className="mb-8">
        <h1 className="section-heading">Công ty tuyển dụng</h1>
        <p className="section-subheading">Khám phá các nhà tuyển dụng hàng đầu trên nền tảng</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {SAMPLE_COMPANIES.map(company => (
          <div key={company.name} className="glass-card p-6 hover:border-brand-500/20 hover:-translate-y-1 transition-all duration-300 group">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 border border-brand-500/20 flex items-center justify-center">
                <Building2 className="w-7 h-7 text-brand-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold group-hover:text-brand-400 transition-colors">{company.name}</h3>
                <p className="text-slate-500 text-xs flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  Việt Nam
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="tag">{company.field}</span>
                <span className="badge-brand text-xs">
                  <Briefcase className="w-3 h-3 mr-1" />
                  {company.jobs} việc làm
                </span>
              </div>
              <Link to="/jobs" className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
                Xem <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
