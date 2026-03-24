import apiClient from './client'

export const jobsApi = {
  list: (params) => apiClient.get('/jobs', { params }),
  get: (jobId) => apiClient.get(`/jobs/${jobId}`),
  create: (data) => apiClient.post('/jobs', data),
}
