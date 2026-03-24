import { create } from 'zustand'
import { authApi } from '../api/auth'

const useAuthStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: false,

  login: (user, token) => {
    localStorage.setItem('token', token)
    set({ user, token, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ isLoading: loading }),

  // Verify token and load user on app start
  initAuth: async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      set({ isLoading: true })
      const res = await authApi.me()
      set({ user: res.data, isAuthenticated: true })
    } catch {
      localStorage.removeItem('token')
      set({ user: null, token: null, isAuthenticated: false })
    } finally {
      set({ isLoading: false })
    }
  },
}))

export default useAuthStore
