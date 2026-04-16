import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { companyApi } from '../../api/employer'
import { useToast } from '../../components/employer/Toast'
import {
  Building2, Globe, MapPin, Users, FileText, Save, Upload,
  Edit2, CheckCircle2, Loader2, Image as ImageIcon
} from 'lucide-react'

const SIZES = ['1-10', '11-50', '51-200', '201-500', '500+']
const INDUSTRIES = [
  'Công nghệ thông tin', 'Tài chính - Ngân hàng', 'Bán lẻ - Thương mại',
  'Y tế - Dược phẩm', 'Giáo dục - Đào tạo', 'Sản xuất - Cơ khí',
  'Marketing - Truyền thông', 'Bất động sản', 'Logistics - Vận tải', 'Khác'
]

function FieldGroup({ label, icon: Icon, children }) {
  return (
    <div>
      <label className="field-label flex items-center gap-1.5">
        {Icon && <Icon size={13} className="text-slate-500" />}
        {label}
      </label>
      {children}
    </div>
  )
}

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-32 glass-card rounded-2xl bg-white/[0.03]" />
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-3 bg-white/5 rounded w-24" />
            <div className="h-10 bg-white/5 rounded-xl" />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CompanyPage() {
  const toast   = useToast()
  const qc      = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form,    setForm]    = useState({
    name: '', description: '', industry: '', size: '', location: '', website: ''
  })

  // ── Fetch existing company ──────────────────────────────────────────────────
  const { data: company, isLoading, error } = useQuery({
    queryKey: ['employer-company'],
    queryFn: () => companyApi.getMe().then(r => r.data),
    retry: false,
    // 404 means no company yet — not a real error
    onError: () => {},
  })

  const hasCompany = !!company && !(error?.message?.includes('404') || error?.response?.status === 404)

  useEffect(() => {
    if (company) {
      setForm({
        name:        company.name        || '',
        description: company.description || '',
        industry:    company.industry    || '',
        size:        company.size        || '',
        location:    company.location    || '',
        website:     company.website     || '',
      })
    }
  }, [company])

  // ── Mutations ───────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (data) => companyApi.create(data),
    onSuccess: () => {
      toast('Tạo công ty thành công! 🎉', 'success')
      qc.invalidateQueries({ queryKey: ['employer-company'] })
      setEditing(false)
    },
    onError: (e) => toast(e.message || 'Tạo thất bại', 'error'),
  })

  const updateMutation = useMutation({
    mutationFn: (data) => companyApi.update(data),
    onSuccess: () => {
      toast('Cập nhật thành công!', 'success')
      qc.invalidateQueries({ queryKey: ['employer-company'] })
      setEditing(false)
    },
    onError: (e) => toast(e.message || 'Cập nhật thất bại', 'error'),
  })

  const logoMutation = useMutation({
    mutationFn: (file) => companyApi.uploadLogo(file),
    onSuccess: () => {
      toast('Tải logo thành công!', 'success')
      qc.invalidateQueries({ queryKey: ['employer-company'] })
    },
    onError: (e) => toast(e.message || 'Tải logo thất bại', 'error'),
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      website:  form.website  || null,
      industry: form.industry || null,
      size:     form.size     || null,
      location: form.location || null,
    }
    if (hasCompany) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0]
    if (file) logoMutation.mutate(file)
  }

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Building2 size={26} className="text-brand-400" />
            Hồ sơ công ty
          </h1>
          <p className="page-subtitle">
            {hasCompany ? 'Quản lý thông tin công ty của bạn' : 'Tạo hồ sơ công ty để bắt đầu tuyển dụng'}
          </p>
        </div>
        {hasCompany && !editing && (
          <button onClick={() => setEditing(true)} className="btn-secondary">
            <Edit2 size={15} /> Chỉnh sửa
          </button>
        )}
      </div>

      {isLoading ? (
        <Skeleton />
      ) : hasCompany && !editing ? (
        /* ── View mode ────────────────────────────────────────────────── */
        <div className="space-y-6">
          {/* Logo + name banner */}
          <div className="glass-card p-6 flex items-center gap-5">
            <div className="relative group">
              <div className="w-20 h-20 rounded-2xl bg-dark-700 border border-white/10 overflow-hidden flex items-center justify-center">
                {company.logo_url
                  ? <img src={company.logo_url} alt="logo" className="w-full h-full object-cover" />
                  : <Building2 size={32} className="text-slate-600" />
                }
              </div>
              <label className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-2xl
                                opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity">
                <Upload size={18} className="text-white" />
                <input type="file" accept="image/*" className="hidden" onChange={handleLogoChange} />
              </label>
              {logoMutation.isPending && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-2xl">
                  <Loader2 size={18} className="text-white animate-spin" />
                </div>
              )}
            </div>
            <div>
              <h2 className="text-white text-xl font-bold">{company.name}</h2>
              {company.slug && <p className="text-slate-500 text-xs mt-0.5">slug: {company.slug}</p>}
              <div className="flex flex-wrap gap-2 mt-2">
                {company.industry && <span className="badge-brand">{company.industry}</span>}
                {company.size     && <span className="badge-gray">{company.size} nhân viên</span>}
              </div>
            </div>
          </div>

          {/* Details grid */}
          <div className="glass-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {[
              { icon: MapPin,   label: 'Địa điểm',  val: company.location },
              { icon: Globe,    label: 'Website',    val: company.website,  link: true },
              { icon: Users,    label: 'Quy mô',     val: company.size ? `${company.size} nhân viên` : null },
              { icon: Building2,label: 'Ngành',      val: company.industry },
            ].map(({ icon: Icon, label, val, link }) => (
              <div key={label} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-brand-600/10 border border-brand-500/20 flex items-center justify-center shrink-0">
                  <Icon size={14} className="text-brand-400" />
                </div>
                <div>
                  <p className="text-slate-500 text-xs">{label}</p>
                  {val
                    ? link
                      ? <a href={val} target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:underline text-sm">{val}</a>
                      : <p className="text-white text-sm font-medium">{val}</p>
                    : <p className="text-slate-600 text-sm">Chưa cập nhật</p>
                  }
                </div>
              </div>
            ))}
          </div>

          {company.description && (
            <div className="glass-card p-6">
              <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                <FileText size={15} className="text-brand-400" /> Giới thiệu
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{company.description}</p>
            </div>
          )}
        </div>
      ) : (
        /* ── Create / Edit form ───────────────────────────────────────── */
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="glass-card p-6 space-y-5">
            <h2 className="section-title">
              {hasCompany ? 'Chỉnh sửa thông tin' : 'Thông tin công ty'}
            </h2>

            <FieldGroup label="Tên công ty *" icon={Building2}>
              <input
                required
                value={form.name}
                onChange={set('name')}
                placeholder="Công ty TNHH XYZ..."
                className="input-field"
              />
            </FieldGroup>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup label="Ngành nghề" icon={Building2}>
                <select value={form.industry} onChange={set('industry')} className="input-field">
                  <option value="">Chọn ngành...</option>
                  {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                </select>
              </FieldGroup>

              <FieldGroup label="Quy mô" icon={Users}>
                <select value={form.size} onChange={set('size')} className="input-field">
                  <option value="">Chọn quy mô...</option>
                  {SIZES.map(s => <option key={s} value={s}>{s} nhân viên</option>)}
                </select>
              </FieldGroup>

              <FieldGroup label="Địa điểm" icon={MapPin}>
                <input
                  value={form.location}
                  onChange={set('location')}
                  placeholder="TP. Hồ Chí Minh"
                  className="input-field"
                />
              </FieldGroup>

              <FieldGroup label="Website" icon={Globe}>
                <input
                  value={form.website}
                  onChange={set('website')}
                  placeholder="https://company.com"
                  className="input-field"
                />
              </FieldGroup>
            </div>

            <FieldGroup label="Giới thiệu công ty" icon={FileText}>
              <textarea
                value={form.description}
                onChange={set('description')}
                rows={5}
                placeholder="Mô tả về công ty, văn hóa, sứ mệnh..."
                className="input-field resize-none"
              />
            </FieldGroup>
          </div>

          <div className="flex items-center gap-3">
            <button type="submit" disabled={isPending} className="btn-primary">
              {isPending ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {hasCompany ? 'Lưu thay đổi' : 'Tạo công ty'}
            </button>
            {hasCompany && (
              <button type="button" onClick={() => setEditing(false)} className="btn-secondary">
                Hủy
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
