import React from 'react'
import { Link } from 'react-router-dom'
import { Building2, Briefcase, MapPin, ArrowRight } from 'lucide-react'

export default function CompanyCard({ company }) {
  const {
    id,
    name,
    industry,
    location,
    job_count,
    logo,
    description,
  } = company

  return (
    <Link
      to={`/companies/${id || name}`}
      className="glass-card p-5 hover:border-slate-200rand-500/20 hover:-translate-y-1 transition-all duration-300 group block"
    >
      <div className="flex items-start gap-4">
        {/* Logo */}
        <div className="w-12 h-12 rounded-xl bg-slate-50radient-to-br from-brand-500/20 to-purple-500/20 border border-slate-200rand-500/20 flex items-center justify-center flex-shrink-0">
          {logo ? (
            <img src={logo} alt={name} className="w-8 h-8 rounded-lg object-cover" />
          ) : (
            <Building2 className="w-6 h-6 text-brand-400" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-slate-900 font-semibold text-sm group-hover:text-brand-400 transition-colors truncate">
            {name}
          </h3>
          {industry && (
            <p className="text-slate-500 text-xs mt-0.5">{industry}</p>
          )}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {location && (
              <span className="tag">
                <MapPin className="w-3 h-3 mr-0.5" />
                {location}
              </span>
            )}
            {job_count != null && (
              <span className="tag">
                <Briefcase className="w-3 h-3 mr-0.5" />
                {job_count} vị trí
              </span>
            )}
          </div>
        </div>

        <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-brand-400 group-hover:translate-x-1 transition-all flex-shrink-0 mt-1" />
      </div>

      {description && (
        <p className="text-slate-500 text-xs mt-3 line-clamp-2 leading-relaxed">
          {description.substring(0, 120)}
        </p>
      )}
    </Link>
  )
}
