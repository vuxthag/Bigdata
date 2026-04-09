import apiClient from './client'

export const usersApi = {
  list: () => apiClient.get('/users'),
  get: (userId) => apiClient.get(`/users/${userId}`),
  me: () => apiClient.get('/users/me'),
  updateMe: (data) => apiClient.put('/users/me', data),
}
