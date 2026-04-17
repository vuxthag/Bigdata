import React from 'react'
import { Cpu } from 'lucide-react'

export default function WelcomeHeader({ user, modelVersion }) {
  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Chào buổi sáng'
    if (h < 18) return 'Chào buổi chiều'
    return 'Chào buổi tối'
  }

  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
          {greeting()}, {user?.full_name?.split(' ').slice(-1)[0] || 'bạn'} 👋
        </h2>
        <p className="text-slate-500 text-sm mt-1.5">Đây là tổng quan hoạt động của bạn hôm nay</p>
      </div>
      <span className="badge-brand text-xs flex items-center gap-1.5">
        <Cpu className="w-3 h-3" />
        {modelVersion?.slice(0, 20) || 'base-model'}
      </span>
    </div>
  )
}
