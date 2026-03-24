import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Upload, Search, FileText, Briefcase, TrendingUp, Cpu, ArrowRight, Clock } from 'lucide-react'
import { analyticsApi } from '../api/analytics'
import useAuthStore from '../store/authStore'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

function StatCard({ icon: Icon, label, value, color = 'brand' }) {
  const colorMap = {
    brand: 'from-brand-500/20 to-brand-600/10 border-brand-500/30 text-brand-400',
    purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/30 text-purple-400',
    emerald: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400',
    amber: 'from-amber-500/20 to-amber-600/10 border-amber-500/30 text-amber-400',
  }
  return (
    <div className={`glass-card p-5 bg-gradient-to-br ${colorMap[color]} border`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className="w-5 h-5 opacity-80" />
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
    </div>
  )
}

function CustomTooltip({ active, payload }) {
  if (active && payload?.length) {
    return (
      <div className="glass-card p-3 text-sm">
        <p className="text-white font-medium">{payload[0].name}</p>
        <p className="text-brand-400">{payload[0].value} lần match</p>
      </div>
    )
  }
  return null
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const { data: stats, isLoading } = useQuery({
    queryKey: ['analytics-stats'],
    queryFn: () => analyticsApi.stats().then(r => r.data),
  })

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Chào buổi sáng'
    if (h < 18) return 'Chào buổi chiều'
    return 'Chào buổi tối'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {greeting()}, {user?.full_name?.split(' ').slice(-1)[0] || 'bạn'} 👋
          </h2>
          <p className="text-slate-400 text-sm mt-1">Đây là tổng quan hoạt động của bạn hôm nay</p>
        </div>
        <div className="badge-brand">
          <Cpu className="w-3 h-3 mr-1" />
          {stats?.model_version?.slice(0, 20) || 'base-model'}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array(4).fill(0).map((_, i) => (
            <div key={i} className="glass-card p-5 animate-pulse h-28 bg-dark-700/50" />
          ))
        ) : (
          <>
            <StatCard icon={FileText} label="CV đã upload" value={stats?.total_cvs ?? 0} color="brand" />
            <StatCard icon={Briefcase} label="Tổng số việc làm" value={stats?.total_jobs?.toLocaleString() ?? 0} color="purple" />
            <StatCard icon={Search} label="Gợi ý đã xem" value={stats?.total_recommendations ?? 0} color="emerald" />
            <StatCard
              icon={TrendingUp}
              label="Điểm match TB"
              value={stats?.avg_similarity_score ? `${(stats.avg_similarity_score * 100).toFixed(1)}%` : '—'}
              color="amber"
            />
          </>
        )}
      </div>

      {/* Top Jobs Chart + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 glass-card p-6">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            Top việc làm bạn quan tâm
          </h3>
          {stats?.top_matched_jobs?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stats.top_matched_jobs} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis dataKey="title" type="category" width={140} tick={{ fill: '#94a3b8', fontSize: 11 }} />
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
        </div>

        {/* Quick Actions */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-white font-semibold">Thao tác nhanh</h3>
          <Link to="/upload" className="flex items-center justify-between p-4 rounded-xl bg-brand-600/10 border border-brand-500/20 hover:bg-brand-600/20 transition-colors group">
            <div className="flex items-center gap-3">
              <Upload className="w-5 h-5 text-brand-400" />
              <div>
                <p className="text-white text-sm font-medium">Upload CV mới</p>
                <p className="text-slate-500 text-xs">PDF hoặc DOCX</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-brand-400 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link to="/recommend" className="flex items-center justify-between p-4 rounded-xl bg-purple-600/10 border border-purple-500/20 hover:bg-purple-600/20 transition-colors group">
            <div className="flex items-center gap-3">
              <Search className="w-5 h-5 text-purple-400" />
              <div>
                <p className="text-white text-sm font-medium">Tìm việc phù hợp</p>
                <p className="text-slate-500 text-xs">AI gợi ý theo CV</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-purple-400 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  )
}
