import apiClient from './client'

export const cvsApi = {
  upload: (formData) =>
    apiClient.post('/cvs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  list: () => apiClient.get('/cvs'),
  delete: (cvId) => apiClient.delete(`/cvs/${cvId}`),
}
