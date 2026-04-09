import React from 'react'
import { Link } from 'react-router-dom'
import { User, CheckCircle, ArrowRight } from 'lucide-react'
import SectionCard from '../../components/layout/SectionCard'

export default function ProfileCompletionCard({ profileFields, completionPct }) {
  return (
    <SectionCard title="Hoàn thiện hồ sơ" titleIcon={User} titleIconColor="text-brand-400">
      <div className="flex items-center gap-4 mb-4">
        {/* Circular progress */}
        <div className="relative w-20 h-20 flex-shrink-0">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
            <path className="text-dark-700" stroke="currentColor" strokeWidth="3" fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path className="text-brand-500" stroke="currentColor" strokeWidth="3" fill="none"
              strokeDasharray={`${completionPct}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-white font-bold text-sm">{completionPct}%</span>
          </div>
        </div>
        <div className="flex-1">
          {Object.entries(profileFields).map(([field, done]) => (
            <div key={field} className="flex items-center gap-2 py-1">
              {done
                ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                : <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />
              }
              <span className={`text-xs ${done ? 'text-slate-400' : 'text-slate-500'}`}>{field}</span>
            </div>
          ))}
        </div>
      </div>
      <Link to="/profile" className="text-brand-400 text-xs hover:text-brand-300 flex items-center gap-1">
        Cập nhật hồ sơ <ArrowRight className="w-3 h-3" />
      </Link>
    </SectionCard>
  )
}
