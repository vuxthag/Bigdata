import apiClient from './client'

export const cvsApi = {
  upload: (formData) =>
    apiClient.post('/cvs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  list: () => apiClient.get('/cvs'),
  get: (cvId) => apiClient.get(`/cvs/${cvId}`),
  delete: (cvId) => apiClient.delete(`/cvs/${cvId}`),
}
