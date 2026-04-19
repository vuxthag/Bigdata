import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { authApi } from '../../api/auth'
import useAuthStore from '../../store/authStore'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function GoogleLoginButton() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const btnRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [gsiReady, setGsiReady] = useState(false)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return

    // Load GSI script if not already present
    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]')
    const initGsi = () => {
      if (!window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
        auto_select: false,
      })
      if (btnRef.current) {
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
        })
      }
      setGsiReady(true)
    }

    if (existingScript) {
      // Script already loaded, just init
      if (window.google?.accounts?.id) {
        initGsi()
      } else {
        existingScript.addEventListener('load', initGsi)
      }
    } else {
      const script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.onload = initGsi
      document.head.appendChild(script)
    }

    return () => {
      // Cleanup not strictly needed for GSI
    }
  }, [])

  const handleCredentialResponse = async (response) => {
    setLoading(true)
    setError('')
    try {
      const res = await authApi.google(response.credential)
      const token = res.data.access_token
      localStorage.setItem('token', token)
      const meRes = await authApi.me()
      login(meRes.data, token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Đăng nhập Google thất bại')
    } finally {
      setLoading(false)
    }
  }

  if (!GOOGLE_CLIENT_ID) {
    return null // Don't render if no client ID configured
  }

  return (
    <div className="w-full">
      {loading && (
        <div className="flex items-center justify-center gap-2 py-2.5 text-sm text-slate-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Đang xử lý...
        </div>
      )}
      <div ref={btnRef} className={`w-full flex justify-center ${loading ? 'hidden' : ''}`} />
      {error && (
        <p className="text-red-400 text-xs text-center mt-2">{error}</p>
      )}
    </div>
  )
}
