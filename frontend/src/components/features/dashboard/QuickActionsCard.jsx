import React from 'react'
import { Link } from 'react-router-dom'
import {
  Upload, Search, Briefcase, TrendingUp, ArrowRight,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import SectionCard from '../../layout/SectionCard'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

function CustomTooltip({ active, payload }) {
  if (active && payload?.length) {
    return (
      <div className="glow-card p-3 text-sm">
        <p className="text-slate-900 font-medium">{payload[0].name}</p>
        <p className="text-brand-400">{payload[0].value} lần match</p>
      </div>
    )
  }
  return null
}

export default function QuickActionsCard({ stats }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Chart */}
      <SectionCard
        title="Top việc làm bạn quan tâm"
        titleIcon={TrendingUp}
        titleIconColor="text-brand-400"
        className="lg:col-span-2"
      >
        {stats?.top_matched_jobs?.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.top_matched_jobs} layout="vertical" margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis 
                dataKey="title" 
                type="category" 
                width={180} 
                tick={{ fill: '#94a3b8', fontSize: 11 }} 
                tickFormatter={(value) => value.length > 25 ? `${value.substring(0, 25)}...` : value}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="match_count" radius={[0, 6, 6, 0]}>
                {stats.top_matched_jobs.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center h-48 text-slate-500 text-sm">
            <Search className="w-10 h-10 mb-3 opacity-30" />
            <p>Chưa có dữ liệu. Hãy upload CV và tìm kiếm việc làm!</p>
          </div>
        )}
      </SectionCard>

      {/* Quick Actions */}
      <SectionCard title="Thao tác nhanh">
        <div className="space-y-4">
          <Link to="/upload" className="flex items-center justify-between p-4 rounded-xl bg-slate-50rand-600/10 border border-slate-200rand-500/20 hover:bg-slate-50rand-600/20 transition-colors group">
            <div className="flex items-center gap-3">
              <Upload className="w-5 h-5 text-brand-400" />
              <div>
                <p className="text-slate-900 text-sm font-medium">Upload CV mới</p>
                <p className="text-slate-500 text-xs">PDF hoặc DOCX</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-brand-400 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link to="/recommend" className="flex items-center justify-between p-4 rounded-xl bg-purple-600/10 border border-purple-500/20 hover:bg-purple-600/20 transition-colors group">
            <div className="flex items-center gap-3">
              <Search className="w-5 h-5 text-purple-400" />
              <div>
                <p className="text-slate-900 text-sm font-medium">Tìm việc phù hợp</p>
                <p className="text-slate-500 text-xs">AI gợi ý theo CV</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-purple-400 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link to="/jobs" className="flex items-center justify-between p-4 rounded-xl bg-emerald-600/10 border border-emerald-500/20 hover:bg-emerald-600/20 transition-colors group">
            <div className="flex items-center gap-3">
              <Briefcase className="w-5 h-5 text-emerald-400" />
              <div>
                <p className="text-slate-900 text-sm font-medium">Duyệt việc làm</p>
                <p className="text-slate-500 text-xs">Hàng trăm cơ hội</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </SectionCard>
    </div>
  )
}
