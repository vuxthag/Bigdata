import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../api/analytics'
import { jobsApi } from '../api/jobs'
import useAuthStore from '../store/authStore'

import PageContainer from '../components/layout/PageContainer'
import WelcomeHeader from '../components/features/dashboard/WelcomeHeader'
import StatsGrid from '../components/features/dashboard/StatsGrid'
import ProfileCompletionCard from '../components/features/dashboard/ProfileCompletionCard'
import AISuggestionCard from '../components/features/dashboard/AISuggestionCard'
import SavedJobsCard from '../components/features/dashboard/SavedJobsCard'
import QuickActionsCard from '../components/features/dashboard/QuickActionsCard'

/* ── Helpers ───────────────────────────────── */
function getSavedJobs() {
  try { return JSON.parse(localStorage.getItem('savedJobs') || '[]') } catch { return [] }
}
function getAppliedJobs() {
  try { return JSON.parse(localStorage.getItem('appliedJobs') || '[]') } catch { return [] }
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const { data: stats, isLoading } = useQuery({
    queryKey: ['analytics-stats'],
    queryFn: () => analyticsApi.stats().then(r => r.data),
  })

  const { data: jobsData } = useQuery({
    queryKey: ['jobs-for-dashboard'],
    queryFn: () => jobsApi.list({ page_size: 100 }).then(r => r.data),
  })

  const savedJobIds = useMemo(() => getSavedJobs(), [])
  const appliedJobsList = useMemo(() => getAppliedJobs(), [])
  const allJobs = jobsData?.items || []

  const savedJobs = useMemo(
    () => allJobs.filter(j => savedJobIds.includes(j.id)).slice(0, 3),
    [allJobs, savedJobIds]
  )

  // Profile completion
  const profileFields = {
    'Tên đầy đủ': !!user?.full_name,
    'Email': !!user?.email,
    'CV đã upload': (stats?.total_cvs ?? 0) > 0,
    'Đã tìm việc': (stats?.total_recommendations ?? 0) > 0,
    'Thông tin cá nhân': !!user?.full_name,
  }
  const completedFields = Object.values(profileFields).filter(Boolean).length
  const totalFields = Object.keys(profileFields).length
  const completionPct = Math.round((completedFields / totalFields) * 100)

  return (
    <PageContainer>
      {/* 1. Welcome Header */}
      <WelcomeHeader user={user} modelVersion={stats?.model_version} />

      {/* 2. Stats Cards */}
      <StatsGrid stats={stats} isLoading={isLoading} />

      {/* 3. Profile Completion + AI Suggestions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ProfileCompletionCard profileFields={profileFields} completionPct={completionPct} />
        <AISuggestionCard />
      </div>

      {/* 4. Saved Jobs + Applied */}
      <SavedJobsCard savedJobs={savedJobs} savedJobIds={savedJobIds} appliedJobsList={appliedJobsList} />

      {/* 5. Chart + Quick Actions */}
      <QuickActionsCard stats={stats} />
    </PageContainer>
  )
}
