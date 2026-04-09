import React from 'react'
import { Link } from 'react-router-dom'
import { Briefcase, Github, Mail, Phone } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="bg-dark-950 border-t border-white/5">
      <div className="section-container py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg">
                <Briefcase className="w-4 h-4 text-white" />
              </div>
              <span className="text-white font-bold text-lg">JobMatch AI</span>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed">
              Nền tảng tìm kiếm việc làm thông minh với AI, 
              sử dụng Sentence-BERT và pgvector để gợi ý chính xác nhất.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">Khám phá</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/jobs" className="text-slate-500 hover:text-brand-400 transition-colors">Việc làm</Link></li>
              <li><Link to="/companies" className="text-slate-500 hover:text-brand-400 transition-colors">Công ty</Link></li>
              <li><Link to="/recommend" className="text-slate-500 hover:text-brand-400 transition-colors">AI Gợi ý</Link></li>
              <li><Link to="/analytics" className="text-slate-500 hover:text-brand-400 transition-colors">Analytics</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">Dành cho bạn</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/upload" className="text-slate-500 hover:text-brand-400 transition-colors">Upload CV</Link></li>
              <li><Link to="/upload-job" className="text-slate-500 hover:text-brand-400 transition-colors">Đăng tin tuyển dụng</Link></li>
              <li><Link to="/dashboard" className="text-slate-500 hover:text-brand-400 transition-colors">Dashboard</Link></li>
              <li><Link to="/profile" className="text-slate-500 hover:text-brand-400 transition-colors">Hồ sơ</Link></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">Liên hệ</h4>
            <ul className="space-y-3 text-sm">
              <li className="flex items-center gap-2 text-slate-500">
                <Mail className="w-4 h-4 text-brand-400" />
                contact@jobmatch.ai
              </li>
              <li className="flex items-center gap-2 text-slate-500">
                <Phone className="w-4 h-4 text-brand-400" />
                +84 999 888 777
              </li>
              <li className="flex items-center gap-2 text-slate-500">
                <Github className="w-4 h-4 text-brand-400" />
                github.com/jobmatch-ai
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/5 mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-slate-600 text-xs">© 2026 JobMatch AI. All rights reserved.</p>
          <div className="flex items-center gap-6 text-xs text-slate-600">
            <span className="hover:text-brand-400 cursor-pointer transition-colors">Privacy</span>
            <span className="hover:text-brand-400 cursor-pointer transition-colors">Terms</span>
            <span className="hover:text-brand-400 cursor-pointer transition-colors">Help</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
