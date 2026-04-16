import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { employerJobsApi } from '../../api/employer'
import { analyticsApi } from '../../api/analytics'
import {
  Briefcase, Users, TrendingUp, Plus, ArrowRight,
  CheckCircle2, Clock, LayoutDashboard, Eye, Award
} from 'lucide-react'
import { JobStatusBadge } from '../../components/employer/StatusBadge'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#818cf8', '#c4b5fd']

function StatCard({ icon: Icon, label, value, color, secondaryLabel, secondaryValue }) {
  return (
    <div className="glass-card p-5 flex flex-col justify-between h-full">
      <div className="flex items-start gap-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
        <div>
          <p className="text-slate-400 text-xs font-medium">{label}</p>
          <p className="text-white text-2xl font-bold mt-0.5">{value}</p>
        </div>
      </div>
      {secondaryLabel && (
        <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
          <span className="text-slate-500 text-xs">{secondaryLabel}</span>
          <span className="text-emerald-400 text-xs font-semibold">{secondaryValue}</span>
        </div>
      )}
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="glass-card p-5 flex items-start gap-4 animate-pulse h-32">
      <div className="w-11 h-11 rounded-xl bg-white/5 shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-white/5 rounded w-20" />
        <div className="h-6 bg-white/5 rounded w-12" />
      </div>
    </div>
  )
}

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

export default function EmployerDashboard() {
  // Fetch Jobs
  const { data: allJobs, isLoading: isJobsLoading } = useQuery({
    queryKey: ['employer-jobs-all'],
    queryFn: () => employerJobsApi.list({ page_size: 100 }).then(r => r.data),
    staleTime: 30_000,
  })

  // Fetch Analytics
  const { data: analytics, isLoading: isAnalyticsLoading } = useQuery({
    queryKey: ['employer-analytics'],
    queryFn: () => analyticsApi.employer().then(r => r.data),
    staleTime: 30_000,
  })

  const jobStats = React.useMemo(() => {
    const items = allJobs?.items || []
    return {
      published: items.filter(j => j.status === 'published').length,
      draft:     items.filter(j => j.status === 'draft').length,
      closed:    items.filter(j => j.status === 'closed').length,
    }
  }, [allJobs])

  const recentJobs = (allJobs?.items || []).slice(0, 5)

  const isLoading = isJobsLoading || isAnalyticsLoading
  const topJobsChartData = analytics?.top_jobs || []

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="page-title flex items-center gap-2">
          <LayoutDashboard size={26} className="text-brand-400" />
          Employer Analytics
        </h1>
        <p className="page-subtitle">Giám sát hiệu quả tuyển dụng và thông tin chi tiết</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard 
              icon={Briefcase} 
              label="Tổng việc làm" 
              value={analytics?.total_jobs || 0} 
              color="bg-gradient-to-br from-brand-600 to-purple-600" 
              secondaryLabel="Đang xuất bản"
              secondaryValue={`${jobStats.published} jobs`}
            />
            <StatCard 
              icon={Users} 
              label="Tổng ứng viên" 
              value={analytics?.total_applications || 0} 
              color="bg-gradient-to-br from-pink-600 to-rose-600"
              secondaryLabel="Lượt xem job"
              secondaryValue={analytics?.total_views}
            />
            <StatCard 
              icon={TrendingUp} 
              label="Tỉ lệ chuyển đổi" 
              value={`${analytics?.conversion_rate || 0}%`} 
              color="bg-gradient-to-br from-emerald-600 to-teal-600"  
              secondaryLabel="Apply / View"
              secondaryValue="Cao"
            />
            <StatCard 
              icon={Clock} 
              label="Tin nháp" 
              value={jobStats.draft} 
              color="bg-gradient-to-br from-amber-500 to-orange-600"
              secondaryLabel="Cần hoàn thiện"
              secondaryValue="Xem ngay"
            />
          </>
        )}
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Việc làm hiệu quả nhất (Top 5)" icon={Award}>
          {topJobsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topJobsChartData} margin={{ left: -10, top: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                <XAxis dataKey="title" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ background: '#1e1e36', border: '1px solid #ffffff15', borderRadius: 12 }} 
                  cursor={{ fill: '#ffffff05' }}
                />
                <Bar dataKey="applications" name="Lượt ứng tuyển" radius={[6, 6, 0, 0]}>
                  {topJobsChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[260px] text-slate-500 text-sm">Chưa có dữ liệu việc làm</div>
          )}
        </ChartCard>

        {/* Quick actions & Tasks */}
        <div className="space-y-4">
          <div className="glass-card p-6 h-full flex flex-col">
             <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Thao tác nhanh
              </h3>
              <div className="grid grid-cols-2 gap-3 flex-1 mb-4">
                <Link to="/employer/jobs/new" className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center gap-2 transition-colors group">
                  <div className="w-10 h-10 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Plus size={20} />
                  </div>
                  <span className="text-sm font-medium text-slate-300">Đăng tin mới</span>
                </Link>
                <Link to="/employer/jobs" className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center gap-2 transition-colors group">
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Briefcase size={20} />
                  </div>
                  <span className="text-sm font-medium text-slate-300">Quản lý tin</span>
                </Link>
              </div>
          </div>
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title">Tin tuyển dụng gần đây</h2>
          <Link to="/employer/jobs" className="btn-ghost text-xs">
            Xem tất cả <ArrowRight size={13} />
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="glass-card p-4 animate-pulse">
                <div className="h-4 bg-white/5 rounded w-1/3 mb-2" />
                <div className="h-3 bg-white/5 rounded w-1/5" />
              </div>
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="glass-card p-10 text-center">
            <p className="text-slate-500 text-sm">Chưa có tin tuyển dụng nào</p>
            <Link to="/employer/jobs/new" className="btn-primary mt-4 mx-auto">
              <Plus size={15} />
              Tạo tin đầu tiên
            </Link>
          </div>
        ) : (
          <div className="glass-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.02]">
                  {['Vị trí','Trạng thái','Ứng viên','Ngày tạo'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {recentJobs.map(job => (
                  <tr key={job.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{job.position_title || '—'}</td>
                    <td className="px-4 py-3"><JobStatusBadge status={job.status} /></td>
                    <td className="px-4 py-3 text-slate-400 flex items-center gap-1.5">
                      <Users size={12} /> {job.applicant_count || 0}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {new Date(job.created_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/employer/jobs/${job.id}`} className="btn-ghost text-xs py-1">
                        Xem <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
