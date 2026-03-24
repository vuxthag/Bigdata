import apiClient from './client'

export const recommendApi = {
  byCV: (data) => apiClient.post('/recommend/by-cv', data),
  byTitle: (data) => apiClient.post('/recommend/by-title', data),
  feedback: (data) => apiClient.post('/recommend/feedback', data),
}
