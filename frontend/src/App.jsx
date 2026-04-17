import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'

// Layouts
import PublicLayout from './components/layout/PublicLayout'

// Public pages
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import JobsPage from './pages/JobsPage'
import JobDetailPage from './pages/JobDetailPage'

// Candidate dashboard (protected)
import DashboardPage from './pages/DashboardPage'
import UploadCVPage from './pages/UploadCVPage'
import RecommendPage from './pages/RecommendPage'
import AnalyticsPage from './pages/AnalyticsPage'
import ProfilePage from './pages/ProfilePage'
import SavedJobsPage from './pages/SavedJobsPage'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { initAuth, isAuthenticated, isLoading } = useAuthStore()

  useEffect(() => {
    initAuth()
  }, [])

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '3rem', height: '3rem',
            border: '4px solid #6366f1',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Đang khởi động...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public layout (navbar + footer) ─── */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
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
          <Route path="/recommend" element={<RecommendPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/saved-jobs" element={<SavedJobsPage />} />
        </Route>

        {/* ── Catch-all ────────────────────────── */}
        <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}
