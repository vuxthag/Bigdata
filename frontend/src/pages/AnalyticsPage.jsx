import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, LineChart, Line, PieChart, Pie, Legend, AreaChart, Area,
} from 'recharts'
import {
  TrendingUp, Cpu, FileText, Briefcase, Search, Star, Users, Activity,
  ArrowUpRight, ArrowDownRight, Server, ShieldAlert
} from 'lucide-react'
import { analyticsApi } from '../api/analytics'
import useAuthStore from '../store/authStore'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#818cf8', '#c4b5fd', '#ddd6fe', '#e0e7ff']
const PIE_COLORS = { applied: '#10b981', saved: '#6366f1', skipped: '#ef4444', viewed: '#94a3b8' }

// Reusable Components
function StatsCard({ icon: Icon, label, value, color, secondaryLabel }) {
  const colorClasses = {
    brand: 'from-brand-600 to-purple-600',
    purple: 'from-purple-600 to-indigo-600',
    emerald: 'from-emerald-600 to-teal-600',
    amber: 'from-amber-500 to-orange-600',
    rose: 'from-rose-500 to-pink-600',
    slate: 'from-slate-600 to-slate-800'
  }
  return (
    <div className="glass-card p-5 flex flex-col justify-between h-full">
      <div className="flex items-start gap-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 bg-slate-50radient-to-br ${colorClasses[color] || colorClasses.brand}`}>
          <Icon size={20} className="text-slate-900" />
        </div>
        <div>
          <p className="text-slate-500 text-xs font-medium">{label}</p>
          <p className="text-slate-900 text-2xl font-bold mt-0.5">{value}</p>
        </div>
      </div>
      {secondaryLabel && (
        <div className="mt-4 pt-4 border-t border-slate-200">
          <span className="text-slate-500 text-xs">{secondaryLabel}</span>
        </div>
      )}
    </div>
  )
}

function ChartCard({ title, icon: Icon, children, className = '' }) {
  return (
    <div className={`glass-card p-6 ${className}`}>
      <h3 className="text-slate-900 font-semibold mb-4 flex items-center gap-2">
        <Icon className="w-4 h-4 text-brand-400" />
        {title}
      </h3>
      {children}
    </div>
  )
}

function AdminAnalytics() {
  const { data: sysStats } = useQuery({ queryKey: ['system-analytics'], queryFn: () => analyticsApi.system().then(r => r.data) })
  const { data: crawlerStats } = useQuery({ queryKey: ['crawler-analytics'], queryFn: () => analyticsApi.crawler().then(r => r.data) })

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard icon={Users} label="Tổng Users" value={sysStats?.total_users || 0} color="emerald" />
        <StatsCard icon={Briefcase} label="Tổng Jobs" value={sysStats?.total_jobs || 0} color="brand" />
        <StatsCard icon={Activity} label="Active Jobs" value={sysStats?.active_jobs || 0} color="purple" />
        <StatsCard icon={Cpu} label="AI Model" value={sysStats?.model_version || 'Latest'} color="rose" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Daily Applications (7 Days)" icon={TrendingUp}>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={sysStats?.daily_applications || []} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} />
              <Area type="monotone" dataKey="count" stroke="#6366f1" fill="#6366f140" strokeWidth={2} name="Ứng tuyển" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Crawler Monitor" icon={Server}>
           <div className="flex flex-col gap-4">
             <div className="grid grid-cols-2 gap-4">
               <div className="p-4 bg-slate-100 rounded-xl text-center">
                 <p className="text-xs text-slate-500 mb-1">Global Error Rate</p>
                 <p className="text-2xl font-bold font-mono text-rose-400">{crawlerStats?.error_rate || 0}%</p>
               </div>
               <div className="p-4 bg-slate-100 rounded-xl text-center">
                 <p className="text-xs text-slate-500 mb-1">Status</p>
                 <p className={`text-xl font-bold flex items-center justify-center gap-2 ${crawlerStats?.is_blocked ? 'text-amber-400' : 'text-emerald-400'}`}>
                   {crawlerStats?.is_blocked ? <><ShieldAlert size={20} /> BLOCKED</>  : 'HEALTHY'}
                 </p>
               </div>
             </div>
             
             <div className="flex-1 mt-2">
               <h4 className="text-sm text-slate-600 font-medium mb-2">Sources Overview</h4>
               {crawlerStats?.jobs_per_source?.map(s => (
                  <div key={s.source} className="flex justify-between items-center p-3 border-slate-200 border-slate-200 last:border-slate-200 hover:bg-slate-100 transition-colors">
                    <span className="text-sm font-semibold capitalize">{s.source}</span>
                    <div className="text-xs text-right">
                      <span className="text-emerald-400 mr-3">Inserted: {s.inserted}</span>
                      <span className="text-rose-400">Errors: {s.errors}</span>
                    </div>
                  </div>
               ))}
               {!crawlerStats?.jobs_per_source?.length && <p className="text-sm text-slate-500 italic mt-4 text-center">No recent crawler runs</p>}
             </div>
           </div>
        </ChartCard>
      </div>
    </div>
  )
}

function CandidateAnalytics() {
  const { data: candStats } = useQuery({ queryKey: ['candidate-analytics'], queryFn: () => analyticsApi.candidate().then(r => r.data) })
  const { data: oldStats } = useQuery({ queryKey: ['old-stats'], queryFn: () => analyticsApi.stats().then(r => r.data) })
  const { data: activity } = useQuery({ queryKey: ['activity'], queryFn: () => analyticsApi.activity().then(r => r.data) })

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard icon={Briefcase} label="Jobs Ứng tuyển" value={candStats?.total_applied || 0} color="brand" secondaryLabel={`${candStats?.recommended_and_applied || 0} từ Recommend AI`} />
        <StatsCard icon={Star} label="Tỉ lệ Phản hồi" value={`${candStats?.success_rate || 0}%`} color="emerald" secondaryLabel={`${candStats?.total_success || 0} Nhận offer / Hired`} />
        <StatsCard icon={Search} label="Việc đã xem" value={candStats?.total_viewed || 0} color="purple" secondaryLabel="Tương tác tổng quan" />
        <StatsCard icon={FileText} label="Số CV (Hệ thống)" value={oldStats?.total_cvs || 0} color="amber" secondaryLabel="Score avg: 85%" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Hoạt động 7 ngày gần nhất" icon={TrendingUp}>
          {activity?.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={activity} margin={{ left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
                <Line type="monotone" dataKey="applied" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} name="Ứng tuyển" />
                <Line type="monotone" dataKey="saved" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} name="Đã lưu" />
                <Line type="monotone" dataKey="skipped" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} name="Bỏ qua" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">Chưa có hoạt động nào</div>
          )}
        </ChartCard>

        <ChartCard title="Top Việc làm Gợi ý AI" icon={Award}>
          {oldStats?.top_matched_jobs?.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={oldStats.top_matched_jobs} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis dataKey="title" type="category" width={110} tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} />
                <Bar dataKey="match_count" radius={[0, 6, 6, 0]} name="Score">
                  {oldStats.top_matched_jobs.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
             <div className="flex items-center justify-center h-48 text-slate-500 text-sm">Cần thêm tương tác để dự đoán</div>
          )}
        </ChartCard>
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">{isAdmin ? 'System Intelligence' : 'My Analytics'}</h2>
          <p className="page-subtitle text-sm mt-1">{isAdmin ? 'Giám sát vận hành và Crawler' : 'Phân tích hoạt động cá nhân và hiệu suất'}</p>
        </div>
        <span className="badge-brand text-xs flex items-center gap-1 shadow-brand">
          <Activity className="w-3 h-3" />
          Real-time Sync
        </span>
      </div>

      {isAdmin ? <AdminAnalytics /> : <CandidateAnalytics />}
    </div>
  )
}
