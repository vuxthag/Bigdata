import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, LineChart, Line, PieChart, Pie, Legend, AreaChart, Area,
} from 'recharts'
import {
  TrendingUp, Cpu, FileText, Briefcase, Search, Star, Users, Activity,
  ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import { analyticsApi } from '../api/analytics'
import StatsCard from '../components/StatsCard'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#818cf8', '#c4b5fd', '#ddd6fe', '#e0e7ff']
const PIE_COLORS = { applied: '#10b981', saved: '#6366f1', skipped: '#ef4444', viewed: '#94a3b8' }

function ChartCard({ title, icon: Icon, children, className = '' }) {
  return (
    <div className={`glass-card p-6 ${className}`}>
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <Icon className="w-4 h-4 text-brand-400" />
        {title}
      </h3>
      {children}
    </div>
  )
}

/* ── Mock data generators ───────────────────── */
function mockUploadTrend() {
  const days = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
  return days.map(d => ({
    day: d,
    cvs: Math.floor(Math.random() * 8) + 1,
    jobs: Math.floor(Math.random() * 12) + 2,
  }))
}

function mockActiveUsers() {
  return [
    { name: 'Nguyễn Văn A', email: 'a@email.com', cvs: 5, searches: 23, last_active: '2 giờ trước' },
    { name: 'Trần Thị B', email: 'b@email.com', cvs: 3, searches: 18, last_active: '5 giờ trước' },
    { name: 'Lê Hoàng C', email: 'c@email.com', cvs: 4, searches: 15, last_active: '1 ngày trước' },
    { name: 'Phạm Đức D', email: 'd@email.com', cvs: 2, searches: 12, last_active: '2 ngày trước' },
    { name: 'Võ Minh E', email: 'e@email.com', cvs: 1, searches: 8, last_active: '3 ngày trước' },
  ]
}

export default function AnalyticsPage() {
  const { data: stats } = useQuery({ queryKey: ['analytics-stats'], queryFn: () => analyticsApi.stats().then(r => r.data) })
  const { data: dist } = useQuery({ queryKey: ['similarity-dist'], queryFn: () => analyticsApi.similarityDistribution().then(r => r.data) })
  const { data: activity } = useQuery({ queryKey: ['activity'], queryFn: () => analyticsApi.activity().then(r => r.data) })

  // Dashboard data (try API, fallback to stats)
  const { data: dashboard } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: () => analyticsApi.dashboard().then(r => r.data).catch(() => null),
  })

  const uploadTrend = mockUploadTrend()
  const activeUsers = mockActiveUsers()

  // Pie chart data
  const pieData = React.useMemo(() => {
    if (!activity?.length) return []
    const totals = { applied: 0, saved: 0, skipped: 0 }
    activity.forEach(d => {
      totals.applied += d.applied || 0
      totals.saved += d.saved || 0
      totals.skipped += d.skipped || 0
    })
    return Object.entries(totals).filter(([,v]) => v > 0).map(([k, v]) => ({
      name: k === 'applied' ? 'Ứng tuyển' : k === 'saved' ? 'Đã lưu' : 'Bỏ qua',
      value: v, key: k,
    }))
  }, [activity])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Analytics</h2>
          <p className="text-slate-400 text-sm mt-1">Phân tích hoạt động và hiệu suất tìm kiếm việc làm</p>
        </div>
        <span className="badge-brand text-xs flex items-center gap-1">
          <Activity className="w-3 h-3" />
          Real-time
        </span>
      </div>

      {/* ── Dashboard Stats Row ─────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatsCard icon={FileText} label="CVs đã upload" value={stats?.total_cvs ?? 0} color="brand" />
        <StatsCard icon={Briefcase} label="Tổng việc làm" value={stats?.total_jobs?.toLocaleString() ?? 0} color="purple" />
        <StatsCard icon={Search} label="Gợi ý đã xem" value={stats?.total_recommendations ?? 0} color="emerald" />
        <StatsCard icon={Users} label="Người dùng" value={dashboard?.total_users ?? stats?.total_users ?? 12} color="amber" />
        <StatsCard icon={Cpu} label="Model" value="SBERT" sub={stats?.model_version?.slice(0,15) || 'base'} color="rose" />
      </div>

      {/* ── Growth Indicators ──────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'CV tuần này', value: '+12', trend: 'up' },
          { label: 'Việc làm mới', value: '+34', trend: 'up' },
          { label: 'Tỉ lệ match', value: '73%', trend: 'up' },
          { label: 'Thời gian TB', value: '2.3s', trend: 'down' },
        ].map(item => (
          <div key={item.label} className="glass-card p-4 flex items-center justify-between">
            <div>
              <p className="text-slate-500 text-xs">{item.label}</p>
              <p className="text-white font-bold text-lg mt-0.5">{item.value}</p>
            </div>
            {item.trend === 'up'
              ? <ArrowUpRight className="w-5 h-5 text-emerald-400" />
              : <ArrowDownRight className="w-5 h-5 text-amber-400" />
            }
          </div>
        ))}
      </div>

      {/* ── Upload Trends (new) ──────────────── */}
      <ChartCard title="Xu hướng tải lên (7 ngày)" icon={TrendingUp}>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={uploadTrend} margin={{ left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
            <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
            <Area type="monotone" dataKey="cvs" stroke="#6366f1" fill="#6366f140" strokeWidth={2} name="CV uploads" />
            <Area type="monotone" dataKey="jobs" stroke="#8b5cf6" fill="#8b5cf640" strokeWidth={2} name="Job uploads" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Charts row 1 ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Phân phối điểm tương đồng" icon={TrendingUp}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={dist || []} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
              <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} labelStyle={{ color: '#e2e8f0' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(dist || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top việc làm được match" icon={Star}>
          {stats?.top_matched_jobs?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stats.top_matched_jobs} layout="vertical" margin={{ left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis dataKey="title" type="category" width={130} tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} labelStyle={{ color: '#e2e8f0' }} />
                <Bar dataKey="match_count" radius={[0, 6, 6, 0]}>
                  {stats.top_matched_jobs.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">Chưa có dữ liệu match</div>
          )}
        </ChartCard>
      </div>

      {/* ── Charts row 2 ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Hoạt động 7 ngày gần nhất" icon={TrendingUp}>
          {activity?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={activity} margin={{ left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
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

        <ChartCard title="Tỉ lệ tương tác" icon={Star}>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} dataKey="value" paddingAngle={3}>
                  {pieData.map((entry, i) => <Cell key={i} fill={PIE_COLORS[entry.key] || COLORS[i]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">Chưa có dữ liệu tương tác</div>
          )}
        </ChartCard>
      </div>

      {/* ── Most Active Users Table (new) ──── */}
      <div className="glass-card p-6">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Users className="w-4 h-4 text-brand-400" />
          Người dùng hoạt động nhiều nhất
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left text-slate-500 font-medium py-3 px-2">#</th>
                <th className="text-left text-slate-500 font-medium py-3 px-2">Người dùng</th>
                <th className="text-left text-slate-500 font-medium py-3 px-2">Email</th>
                <th className="text-center text-slate-500 font-medium py-3 px-2">CVs</th>
                <th className="text-center text-slate-500 font-medium py-3 px-2">Tìm kiếm</th>
                <th className="text-right text-slate-500 font-medium py-3 px-2">Hoạt động</th>
              </tr>
            </thead>
            <tbody>
              {activeUsers.map((u, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                  <td className="py-3 px-2 text-slate-600">{i + 1}</td>
                  <td className="py-3 px-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                        {u.name[0]}
                      </div>
                      <span className="text-white font-medium">{u.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-slate-400">{u.email}</td>
                  <td className="py-3 px-2 text-center text-brand-400 font-medium">{u.cvs}</td>
                  <td className="py-3 px-2 text-center text-purple-400 font-medium">{u.searches}</td>
                  <td className="py-3 px-2 text-right text-slate-500 text-xs">{u.last_active}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
