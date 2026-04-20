import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  FileText, Briefcase, Bookmark, Send, Eye, SkipForward,
  TrendingUp, Brain, Upload, Search, ArrowRight, Clock,
  Building2, CheckCircle, User, Zap, Cpu, MapPin,
  Activity, Target, Sparkles,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, AreaChart, Area,
} from 'recharts'
import { analyticsApi } from '../api/analytics'
import useAuthStore from '../store/authStore'
import PageContainer from '../components/layout/PageContainer'
import SectionCard from '../components/layout/SectionCard'

/* ── Helpers ──────────────────────────────── */
const ACTION_LABELS = { viewed: 'Đã xem', applied: 'Đã ứng tuyển', saved: 'Đã lưu', skipped: 'Bỏ qua' }
const ACTION_COLORS = {
  viewed:  'text-blue-500 bg-blue-50 border-blue-200',
  applied: 'text-emerald-500 bg-emerald-50 border-emerald-200',
  saved:   'text-amber-500 bg-amber-50 border-amber-200',
  skipped: 'text-slate-400 bg-slate-50 border-slate-200',
}
const ACTION_ICONS = { viewed: Eye, applied: Send, saved: Bookmark, skipped: SkipForward }
const CHART_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Chào buổi sáng'
  if (h < 18) return 'Chào buổi chiều'
  return 'Chào buổi tối'
}

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'Vừa xong'
  if (m < 60) return `${m} phút trước`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} giờ trước`
  const d = Math.floor(h / 24)
  return `${d} ngày trước`
}

/* ── Stat Card ────────────────────────────── */
function StatCard({ icon: Icon, label, value, color, subLabel }) {
  const colorMap = {
    brand:   'from-brand-500/20 to-brand-600/10',
    purple:  'from-purple-500/20 to-purple-600/10',
    emerald: 'from-emerald-500/20 to-emerald-600/10',
    amber:   'from-amber-500/20 to-amber-600/10',
    blue:    'from-blue-500/20 to-blue-600/10',
    rose:    'from-rose-500/20 to-rose-600/10',
  }
  return (
    <div className={`glow-card p-5 bg-gradient-to-br ${colorMap[color] || ''} border border-slate-200 hover:-translate-y-1 transition-all duration-300`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className="w-5 h-5 opacity-80 text-slate-900/60" />
        <span className="text-slate-500 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
      {subLabel && <p className="text-xs text-slate-400 mt-1">{subLabel}</p>}
    </div>
  )
}

/* ── Custom Tooltip ──────────────────────── */
function ChartTooltip({ active, payload }) {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-lg text-sm">
        <p className="text-slate-900 font-medium">{payload[0]?.payload?.title || payload[0]?.payload?.date}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-brand-500">{p.value} {p.name || 'lần'}</p>
        ))}
      </div>
    )
  }
  return null
}

/* ══════════════════════════════════════════════
   MAIN DASHBOARD
   ══════════════════════════════════════════════ */
export default function DashboardPage() {
  const { user } = useAuthStore()

  const { data: db, isLoading } = useQuery({
    queryKey: ['user-dashboard'],
    queryFn: () => analyticsApi.userDashboard().then(r => r.data),
    refetchOnWindowFocus: true,
  })

  const counts = db?.counts || {}
  const savedJobs = db?.saved_jobs || []
  const appliedJobs = db?.applied_jobs || []
  const recentActivity = db?.recent_activity || []
  const cvs = db?.cvs || []
  const topJobs = db?.top_matched_jobs || []
  const activityByDay = db?.activity_by_day || []

  // ── Profile completion (based on real data) ──
  const profileFields = useMemo(() => ({
    'Tên đầy đủ': !!user?.full_name,
    'Email': !!user?.email,
    'CV đã upload': counts.cvs > 0,
    'Đã dùng AI gợi ý': counts.viewed > 0,
    'Đã lưu / ứng tuyển': (counts.saved + counts.applied) > 0,
  }), [user, counts])
  const completedCount = Object.values(profileFields).filter(Boolean).length
  const completionPct = Math.round((completedCount / Object.keys(profileFields).length) * 100)

  // ── Dynamic AI suggestions ──
  const suggestions = useMemo(() => {
    const items = []
    if (counts.cvs === 0) {
      items.push({ icon: Upload, text: 'Upload CV đầu tiên để bắt đầu tìm việc', link: '/upload', color: 'brand' })
    }
    if (counts.viewed === 0 && counts.cvs > 0) {
      items.push({ icon: Brain, text: 'Dùng AI phân tích CV và tìm việc phù hợp', link: '/recommend', color: 'purple' })
    }
    if (counts.cvs > 0 && counts.viewed > 0 && counts.applied === 0) {
      items.push({ icon: Send, text: 'Bạn chưa ứng tuyển việc nào! Hãy xem lại gợi ý AI', link: '/recommend', color: 'emerald' })
    }
    if (counts.cvs > 0 && counts.cvs < 3) {
      items.push({ icon: FileText, text: 'Upload thêm CV để AI so sánh và phân tích đa dạng hơn', link: '/upload', color: 'amber' })
    }
    if (items.length === 0) {
      items.push({ icon: Sparkles, text: 'Tiếp tục khám phá việc làm mới', link: '/jobs', color: 'brand' })
      items.push({ icon: Brain, text: 'Phân tích CV để cập nhật gợi ý', link: '/recommend', color: 'purple' })
    }
    items.push({ icon: Briefcase, text: 'Duyệt hàng nghìn việc làm', link: '/jobs', color: 'emerald' })
    return items.slice(0, 3)
  }, [counts])

  // ── Loading skeleton ──
  if (isLoading) {
    return (
      <PageContainer>
        <div className="animate-pulse space-y-6">
          <div className="h-16 bg-slate-100 rounded-2xl" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{Array(4).fill(0).map((_, i) => <div key={i} className="h-28 bg-slate-100 rounded-2xl" />)}</div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{Array(2).fill(0).map((_, i) => <div key={i} className="h-48 bg-slate-100 rounded-2xl" />)}</div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>

      {/* ── 1. Welcome Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
            {greeting()}, {user?.full_name?.split(' ').slice(-1)[0] || 'bạn'} 👋
          </h2>
          <p className="text-slate-500 text-sm mt-1.5">Tổng quan hoạt động và tiến trình tìm việc của bạn</p>
        </div>
        <span className="badge-brand text-xs flex items-center gap-1.5">
          <Cpu className="w-3 h-3" />
          {db?.model_version?.slice(0, 20) || 'base-model'}
        </span>
      </div>

      {/* ── 2. Stats Grid (real data) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="CV đã upload" value={counts.cvs ?? 0} color="brand" />
        <StatCard icon={Eye} label="Lượt gợi ý đã xem" value={counts.viewed ?? 0} color="purple" />
        <StatCard icon={Bookmark} label="Việc đã lưu" value={counts.saved ?? 0} color="amber" />
        <StatCard
          icon={TrendingUp}
          label="Điểm match TB"
          value={db?.avg_similarity ? `${(db.avg_similarity * 100).toFixed(1)}%` : '—'}
          color="emerald"
          subLabel={counts.applied > 0 ? `${counts.applied} lần ứng tuyển` : null}
        />
      </div>

      {/* ── 3. Profile Completion + Dynamic AI Suggestions ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Profile Completion */}
        <SectionCard title="Hoàn thiện hồ sơ" titleIcon={User} titleIconColor="text-brand-400">
          <div className="flex items-center gap-4 mb-4">
            <div className="relative w-20 h-20 flex-shrink-0">
              <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
                <path className="text-slate-200" stroke="currentColor" strokeWidth="3" fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="text-brand-500" stroke="currentColor" strokeWidth="3" fill="none"
                  strokeDasharray={`${completionPct}, 100`}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-slate-900 font-bold text-sm">{completionPct}%</span>
              </div>
            </div>
            <div className="flex-1">
              {Object.entries(profileFields).map(([field, done]) => (
                <div key={field} className="flex items-center gap-2 py-1">
                  {done
                    ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    : <div className="w-3.5 h-3.5 rounded-full border border-slate-300" />
                  }
                  <span className={`text-xs ${done ? 'text-slate-600' : 'text-slate-400'}`}>{field}</span>
                </div>
              ))}
            </div>
          </div>
          {/* CVs uploaded */}
          {cvs.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100">
              <p className="text-[10px] text-slate-400 mb-2">CV của bạn:</p>
              {cvs.slice(0, 3).map(cv => (
                <div key={cv.id} className="flex items-center gap-2 py-1">
                  <FileText className="w-3 h-3 text-brand-400" />
                  <span className="text-xs text-slate-600 truncate flex-1">{cv.filename}</span>
                  <span className="text-[10px] text-slate-400">{timeAgo(cv.uploaded_at)}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        {/* AI Suggestions (dynamic) */}
        <SectionCard title="Gợi ý cho bạn" titleIcon={Zap} titleIconColor="text-amber-400">
          <div className="space-y-3">
            {suggestions.map((item, i) => (
              <Link key={i} to={item.link}
                className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 hover:bg-white transition-all group">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-${item.color}-50 border border-${item.color}-200`}>
                  <item.icon className={`w-4 h-4 text-${item.color}-500`} />
                </div>
                <span className="text-slate-600 text-sm flex-1">{item.text}</span>
                <ArrowRight className="w-3 h-3 text-slate-400 group-hover:translate-x-1 transition-transform" />
              </Link>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-3 gap-2">
            <Link to="/upload" className="text-center p-2 rounded-lg hover:bg-slate-50 transition-colors">
              <Upload className="w-4 h-4 mx-auto text-brand-400 mb-1" />
              <span className="text-[10px] text-slate-500">Upload CV</span>
            </Link>
            <Link to="/recommend" className="text-center p-2 rounded-lg hover:bg-slate-50 transition-colors">
              <Brain className="w-4 h-4 mx-auto text-purple-400 mb-1" />
              <span className="text-[10px] text-slate-500">AI Gợi ý</span>
            </Link>
            <Link to="/jobs" className="text-center p-2 rounded-lg hover:bg-slate-50 transition-colors">
              <Briefcase className="w-4 h-4 mx-auto text-emerald-400 mb-1" />
              <span className="text-[10px] text-slate-500">Việc làm</span>
            </Link>
          </div>
        </SectionCard>
      </div>

      {/* ── 4. Saved Jobs + Applied Jobs (from DB) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Saved Jobs */}
        <SectionCard title={`Việc đã lưu (${counts.saved})`} titleIcon={Bookmark} titleIconColor="text-amber-400">
          {savedJobs.length > 0 ? (
            <div className="space-y-2">
              {savedJobs.slice(0, 5).map(job => (
                <Link key={job.job_id} to={`/jobs/${job.job_id}`}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors group">
                  <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0">
                    <Bookmark className="w-4 h-4 text-amber-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-900 text-sm font-medium truncate">{job.position_title}</p>
                    <p className="text-slate-500 text-xs flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> {job.company || '—'}
                      {job.similarity_score > 0 && (
                        <span className="ml-2 text-emerald-500 font-medium">{(job.similarity_score * 100).toFixed(0)}% match</span>
                      )}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-400">{timeAgo(job.saved_at)}</span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <Bookmark className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">Chưa lưu việc nào</p>
              <Link to="/recommend" className="text-brand-400 text-xs hover:text-brand-500 mt-1 inline-block">
                Dùng AI tìm việc phù hợp →
              </Link>
            </div>
          )}
        </SectionCard>

        {/* Applied Jobs */}
        <SectionCard title={`Đã ứng tuyển (${counts.applied})`} titleIcon={Send} titleIconColor="text-emerald-400">
          {appliedJobs.length > 0 ? (
            <div className="space-y-2">
              {appliedJobs.slice(0, 5).map(job => (
                <Link key={job.job_id} to={`/jobs/${job.job_id}`}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors group">
                  <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center flex-shrink-0">
                    <Send className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-900 text-sm font-medium truncate">{job.position_title}</p>
                    <p className="text-slate-500 text-xs flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> {job.company || '—'}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">Đã gửi</span>
                    <p className="text-[10px] text-slate-400 mt-0.5">{timeAgo(job.applied_at)}</p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <Send className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">Chưa ứng tuyển việc nào</p>
              <Link to="/recommend" className="text-brand-400 text-xs hover:text-brand-500 mt-1 inline-block">
                Xem gợi ý AI và ứng tuyển →
              </Link>
            </div>
          )}
        </SectionCard>
      </div>

      {/* ── 5. Recent Activity Feed + Top Matched Chart ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Recent Activity */}
        <SectionCard title="Hoạt động gần đây" titleIcon={Activity} titleIconColor="text-blue-400" className="lg:col-span-3">
          {recentActivity.length > 0 ? (
            <div className="space-y-1 max-h-[340px] overflow-y-auto pr-1">
              {recentActivity.map(act => {
                const Icon = ACTION_ICONS[act.action] || Eye
                const colorCls = ACTION_COLORS[act.action] || ACTION_COLORS.viewed
                return (
                  <Link key={act.id} to={`/jobs/${act.job_id}`}
                    className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50 transition-colors">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center border ${colorCls} flex-shrink-0`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-800 text-xs font-medium truncate">{act.position_title}</p>
                      <p className="text-slate-400 text-[10px] flex items-center gap-1">
                        {act.company && <><Building2 className="w-2.5 h-2.5" /> {act.company}</>}
                        {act.similarity_score > 0 && <span className="ml-1 text-emerald-500">{(act.similarity_score * 100).toFixed(0)}%</span>}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-medium border ${colorCls}`}>
                        {ACTION_LABELS[act.action]}
                      </span>
                      <p className="text-[9px] text-slate-400 mt-0.5">{timeAgo(act.created_at)}</p>
                    </div>
                  </Link>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-10">
              <Activity className="w-10 h-10 text-slate-200 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">Chưa có hoạt động nào</p>
              <p className="text-slate-400 text-xs mt-1">Hãy upload CV và dùng AI gợi ý để bắt đầu!</p>
            </div>
          )}
        </SectionCard>

        {/* Top Matched Jobs Chart */}
        <SectionCard title="Top việc phù hợp" titleIcon={Target} titleIconColor="text-brand-400" className="lg:col-span-2">
          {topJobs.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topJobs} layout="vertical" margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  dataKey="title"
                  type="category"
                  width={120}
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  tickFormatter={v => v.length > 18 ? `${v.substring(0, 18)}…` : v}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="match_count" name="Lần match" radius={[0, 6, 6, 0]}>
                  {topJobs.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-10">
              <Search className="w-10 h-10 text-slate-200 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">Chưa có dữ liệu</p>
              <p className="text-slate-400 text-xs mt-1">Dùng AI gợi ý để có dữ liệu ở đây</p>
            </div>
          )}
        </SectionCard>
      </div>

      {/* ── 6. Activity Trend (7 days) ── */}
      {activityByDay.length > 0 && (
        <SectionCard title="Xu hướng hoạt động 7 ngày" titleIcon={TrendingUp} titleIconColor="text-purple-400">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={activityByDay} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gradViewed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradApplied" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Area type="monotone" dataKey="viewed" name="Đã xem" stroke="#6366f1" fill="url(#gradViewed)" strokeWidth={2} />
              <Area type="monotone" dataKey="applied" name="Ứng tuyển" stroke="#10b981" fill="url(#gradApplied)" strokeWidth={2} />
              <Area type="monotone" dataKey="saved" name="Đã lưu" stroke="#f59e0b" fill="none" strokeWidth={1.5} strokeDasharray="4 2" />
            </AreaChart>
          </ResponsiveContainer>
        </SectionCard>
      )}

    </PageContainer>
  )
}
