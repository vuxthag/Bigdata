import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'

// Providers
import { ToastProvider } from './components/employer/Toast'

// Layouts
import PublicLayout from './components/layout/PublicLayout'
import EmployerLayout from './components/employer/EmployerLayout'

// Public pages
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import JobsPage from './pages/JobsPage'
import JobDetailPage from './pages/JobDetailPage'
import CompaniesPage from './pages/CompaniesPage'
import CompanyDetailPage from './pages/CompanyDetailPage'

// Dashboard pages (protected)
import DashboardPage from './pages/DashboardPage'
import UploadCVPage from './pages/UploadCVPage'
import UploadJobPage from './pages/UploadJobPage'
import RecommendPage from './pages/RecommendPage'
import AnalyticsPage from './pages/AnalyticsPage'
import ProfilePage from './pages/ProfilePage'
import SavedJobsPage from './pages/SavedJobsPage'
import AppliedJobsPage from './pages/AppliedJobsPage'

// Employer pages
import EmployerDashboard from './pages/employer/Dashboard'
import EmployerCompany   from './pages/employer/Company'
import EmployerJobs      from './pages/employer/Jobs'
import EmployerNewJob    from './pages/employer/NewJob'
import EmployerJobDetail from './pages/employer/JobDetail'
import EmployerApplications from './pages/employer/Applications'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function EmployerRoute({ children }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (user && user.role !== 'employer') return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  const { initAuth, isAuthenticated, isLoading } = useAuthStore()

  useEffect(() => {
    initAuth()
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-900">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Đang khởi động...</p>
        </div>
      </div>
    )
  }

  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* ── Public layout (navbar + footer) ─── */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/companies" element={<CompaniesPage />} />
            <Route path="/companies/:companyId" element={<CompanyDetailPage />} />
          </Route>

          {/* ── Auth pages (standalone, no layout) ─ */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* ── Candidate dashboard (protected) ─── */}
          <Route
            element={
              <ProtectedRoute>
                <PublicLayout hideFooter />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadCVPage />} />
            <Route path="/upload-job" element={<UploadJobPage />} />
            <Route path="/recommend" element={<RecommendPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/saved-jobs" element={<SavedJobsPage />} />
            <Route path="/applied-jobs" element={<AppliedJobsPage />} />
          </Route>

          {/* ── Employer dashboard (role-protected) ─ */}
          <Route
            element={
              <EmployerRoute>
                <EmployerLayout />
              </EmployerRoute>
            }
          >
            <Route path="/employer"             element={<EmployerDashboard />} />
            <Route path="/employer/company"     element={<EmployerCompany />} />
            <Route path="/employer/jobs"        element={<EmployerJobs />} />
            <Route path="/employer/jobs/new"    element={<EmployerNewJob />} />
            <Route path="/employer/jobs/:jobId" element={<EmployerJobDetail />} />
            <Route path="/employer/applications/:jobId" element={<EmployerApplications />} />
          </Route>

          {/* ── Catch-all ────────────────────────── */}
          <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/'} replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
