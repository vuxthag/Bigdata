import React from 'react'
import { Link } from 'react-router-dom'
import { Zap, Target, Search, Briefcase, ArrowRight } from 'lucide-react'
import SectionCard from '../../layout/SectionCard'

const suggestions = [
  { icon: Target, text: 'Upload thêm CV để AI phân tích kỹ năng chính xác hơn', link: '/upload', color: 'brand' },
  { icon: Search, text: 'Thử tìm kiếm theo chức danh để khám phá cơ hội mới', link: '/recommend', color: 'purple' },
  { icon: Briefcase, text: 'Xem các việc làm phổ biến phù hợp với CV của bạn', link: '/jobs', color: 'emerald' },
]

export default function AISuggestionCard() {
  return (
    <SectionCard title="Gợi ý AI cho bạn" titleIcon={Zap} titleIconColor="text-amber-400">
      <div className="space-y-3">
        {suggestions.map((item, i) => (
          <Link key={i} to={item.link}
            className={`flex items-center gap-3 p-3 rounded-xl bg-${item.color}-500/5 border border-${item.color}-500/10 hover:bg-${item.color}-500/10 transition-colors group`}>
            <item.icon className={`w-4 h-4 text-${item.color}-400`} />
            <span className="text-slate-600 text-sm flex-1">{item.text}</span>
            <ArrowRight className={`w-3 h-3 text-${item.color}-400 group-hover:translate-x-1 transition-transform`} />
          </Link>
        ))}
      </div>
    </SectionCard>
  )
}
