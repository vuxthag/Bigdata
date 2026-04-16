import React, { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { employerJobsApi, employerApplicationsApi } from '../../api/employer'
import { useToast } from '../../components/employer/Toast'
import ApplicationTable from '../../components/employer/ApplicationTable'
import { JobStatusBadge } from '../../components/employer/StatusBadge'
import { ArrowLeft, Users, Briefcase, Loader2 } from 'lucide-react'

export default function ApplicationsPage() {
  const { jobId }  = useParams()
  const navigate   = useNavigate()
  const toast      = useToast()
  const qc         = useQueryClient()
  const [updatingId, setUpdatingId] = useState(null)

  // We need jobId from route params — if going to /employer/applications/:jobId
  // Or we might navigate here from JobDetail. This page is standalone.

  const { data: job } = useQuery({
    queryKey: ['employer-job', jobId],
    queryFn: () => employerJobsApi.get(jobId).then(r => r.data),
    enabled: !!jobId,
    staleTime: 60_000,
  })

  const { data: appsData, isLoading } = useQuery({
    queryKey: ['employer-applications', jobId],
    queryFn: () => employerApplicationsApi.listByJob(jobId).then(r => r.data),
    enabled: !!jobId,
    staleTime: 30_000,
  })

  const statusMutation = useMutation({
    mutationFn: ({ appId, status }) => employerApplicationsApi.updateStatus(appId, status),
    onSuccess: () => {
      toast('Cập nhật trạng thái thành công!', 'success')
      qc.invalidateQueries({ queryKey: ['employer-applications', jobId] })
      qc.invalidateQueries({ queryKey: ['employer-job', jobId] })
      setUpdatingId(null)
    },
    onError: (e) => {
      toast(e.message || 'Cập nhật thất bại', 'error')
      setUpdatingId(null)
    },
  })

  const handleStatusUpdate = (appId, status) => {
    setUpdatingId(appId)
    statusMutation.mutate({ appId, status })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => jobId ? navigate(`/employer/jobs/${jobId}`) : navigate('/employer/jobs')}
          className="btn-ghost p-2"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Users size={24} className="text-brand-400" />
            Danh sách ứng viên
          </h1>
          {job && (
            <div className="flex items-center gap-2 mt-1">
              <p className="page-subtitle">
                <span className="text-slate-300">{job.position_title}</span>
              </p>
              <JobStatusBadge status={job.status} />
            </div>
          )}
        </div>

        {job && (
          <div className="ml-auto">
            <Link to={`/employer/jobs/${jobId}`} className="btn-secondary text-sm">
              <Briefcase size={14} /> Chi tiết job
            </Link>
          </div>
        )}
      </div>

      {/* Stats */}
      {appsData && (
        <div className="flex gap-4 flex-wrap">
          {[
            { status: 'applied',   label: 'Mới nộp'    },
            { status: 'reviewed',  label: 'Đã xem'      },
            { status: 'interview', label: 'Phỏng vấn'   },
            { status: 'offered',   label: 'Đã offer'    },
            { status: 'hired',     label: 'Đã tuyển'    },
            { status: 'rejected',  label: 'Từ chối'     },
          ].map(({ status, label }) => {
            const count = appsData.items.filter(a => a.status === status).length
            return (
              <div key={status} className="glass-card px-4 py-3 text-center min-w-[80px]">
                <p className="text-white font-bold text-lg">{count}</p>
                <p className="text-slate-500 text-xs">{label}</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Table */}
      <ApplicationTable
        applications={appsData?.items || []}
        isLoading={isLoading}
        onUpdateStatus={handleStatusUpdate}
        updatingId={updatingId}
      />
    </div>
  )
}
