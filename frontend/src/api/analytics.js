import apiClient from './client'

export const analyticsApi = {
  stats: () => apiClient.get('/analytics/stats'),
  similarityDistribution: () => apiClient.get('/analytics/similarity-distribution'),
  activity: () => apiClient.get('/analytics/activity'),
}
