import apiClient from './client'

export const analyticsApi = {
  stats: () => apiClient.get('/analytics/stats'),
  dashboard: () => apiClient.get('/analytics/dashboard'),
  similarityDistribution: () => apiClient.get('/analytics/similarity-distribution'),
  similarity: () => apiClient.get('/analytics/similarity'),
  activity: () => apiClient.get('/analytics/activity'),
  topJobs: () => apiClient.get('/analytics/top-jobs'),
  
  // Phase 5 Additions
  candidate: () => apiClient.get('/candidate/analytics'),
  employer: () => apiClient.get('/employer/analytics'),
  system: () => apiClient.get('/system/analytics'),
  crawler: () => apiClient.get('/crawler/analytics'),
}
