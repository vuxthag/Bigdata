import React from 'react'
import { FileText, Users } from 'lucide-react'

const tabs = [
  { key: 'cv', icon: FileText, label: '📄 Việc làm cho CV' },
  { key: 'candidates', icon: Users, label: '👥 Ứng viên cho vị trí' },
]

export default function SuggestionTabs({ activeTab, onTabChange }) {
  return (
    <div className="flex gap-2 p-1.5 bg-dark-700/50 rounded-2xl">
      {tabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onTabChange(key)}
          className={`flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-300
            ${activeTab === key
              ? 'bg-gradient-to-r from-brand-600 to-purple-600 text-white shadow-lg shadow-brand-600/25'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
