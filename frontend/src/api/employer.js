import apiClient from './client'

// ── Company ───────────────────────────────────────────────────────────────────

export const companyApi = {
  /** GET /employer/company/me */
  getMe: () => apiClient.get('/employer/company/me'),

  /** POST /employer/company */
  create: (data) => apiClient.post('/employer/company', data),

  /** PUT /employer/company/me */
  update: (data) => apiClient.put('/employer/company/me', data),

  /** POST /employer/company/logo  (multipart) */
  uploadLogo: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post('/employer/company/logo', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export const employerJobsApi = {
  /** GET /employer/jobs?status=&page=&page_size= */
  list: (params = {}) => apiClient.get('/employer/jobs', { params }),

  /** GET /employer/jobs/:id */
  get: (id) => apiClient.get(`/employer/jobs/${id}`),

  /** POST /employer/jobs */
  create: (data) => apiClient.post('/employer/jobs', data),

  /** PUT /employer/jobs/:id */
  update: (id, data) => apiClient.put(`/employer/jobs/${id}`, data),

  /** PATCH /employer/jobs/:id/publish */
  publish: (id) => apiClient.patch(`/employer/jobs/${id}/publish`),

  /** PATCH /employer/jobs/:id/close */
  close: (id) => apiClient.patch(`/employer/jobs/${id}/close`),

  /** DELETE /employer/jobs/:id */
  delete: (id) => apiClient.delete(`/employer/jobs/${id}`),
}

// ── Applications ──────────────────────────────────────────────────────────────

export const employerApplicationsApi = {
  /** GET /employer/applications/:jobId */
  listByJob: (jobId) => apiClient.get(`/employer/applications/${jobId}`),

  /** PATCH /employer/applications/:appId/status */
  updateStatus: (appId, status) =>
    apiClient.patch(`/employer/applications/${appId}/status`, { status }),
}
