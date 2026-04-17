import React from 'react'
import { Search, Loader2 } from 'lucide-react'

export default function SuggestionButton({ loading, activeTab, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full inline-flex items-center justify-center gap-2 
        px-6 py-3.5 rounded-xl text-sm font-semibold
        bg-slate-50radient-to-r from-brand-600 to-purple-600
        hover:from-brand-500 hover:to-purple-500
        text-slate-900 transition-all duration-300
        shadow-lg shadow-brand-600/30
        hover:shadow-brand-500/40 hover:shadow-xl
        hover:-translate-y-0.5
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
      {loading ? 'Đang tìm kiếm...' : activeTab === 'cv' ? 'Tìm việc phù hợp' : 'Tìm ứng viên phù hợp'}
    </button>
  )
}
