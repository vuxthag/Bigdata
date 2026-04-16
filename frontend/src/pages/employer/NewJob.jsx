import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { employerJobsApi } from '../../api/employer'
import { useToast } from '../../components/employer/Toast'
import {
  Briefcase, MapPin, DollarSign, Calendar, Tag,
  ArrowLeft, Save, Loader2, X, Plus
} from 'lucide-react'

const JOB_TYPES = [
  { value: 'full_time',  label: 'Full-time'  },
  { value: 'part_time',  label: 'Part-time'  },
  { value: 'contract',   label: 'Hợp đồng'  },
  { value: 'internship', label: 'Thực tập'  },
  { value: 'remote',     label: 'Remote'     },
]

const INITIAL = {
  position_title: '',
  description: '',
  location: '',
  job_type: 'full_time',
  salary_min: '',
  salary_max: '',
  deadline: '',
  skills: [],
}

function SkillInput({ skills, onChange }) {
  const [input, setInput] = useState('')

  const add = () => {
    const trimmed = input.trim()
    if (trimmed && !skills.includes(trimmed)) {
      onChange([...skills, trimmed])
    }
    setInput('')
  }

  const remove = (s) => onChange(skills.filter(x => x !== s))

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="Nhập skill rồi Enter..."
          className="input-field flex-1 py-2.5 text-sm"
        />
        <button type="button" onClick={add} className="btn-secondary px-3">
          <Plus size={14} />
        </button>
      </div>
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {skills.map(s => (
            <span key={s} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-600/20 border border-brand-500/30 text-brand-300 text-xs font-medium">
              {s}
              <button type="button" onClick={() => remove(s)} className="hover:text-red-400 transition-colors">
                <X size={11} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function FieldGroup({ label, icon: Icon, required, children, hint }) {
  return (
    <div>
      <label className="field-label flex items-center gap-1.5">
        {Icon && <Icon size={12} className="text-slate-500" />}
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-600 mt-1">{hint}</p>}
    </div>
  )
}

export default function NewJobPage() {
  const toast    = useToast()
  const navigate = useNavigate()
  const qc       = useQueryClient()
  const [form, setForm] = useState(INITIAL)

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  const mutation = useMutation({
    mutationFn: (data) => employerJobsApi.create(data),
    onSuccess: (res) => {
      toast('Tạo tin nháp thành công! ✅', 'success')
      qc.invalidateQueries({ queryKey: ['employer-jobs'] })
      qc.invalidateQueries({ queryKey: ['employer-jobs-all'] })
      navigate(`/employer/jobs/${res.data.job_id}`)
    },
    onError: (e) => toast(e.message || 'Tạo tin thất bại', 'error'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    mutation.mutate({
      position_title: form.position_title,
      description:    form.description    || null,
      location:       form.location       || null,
      job_type:       form.job_type       || null,
      salary_min:     form.salary_min     ? Number(form.salary_min)  : null,
      salary_max:     form.salary_max     ? Number(form.salary_max)  : null,
      deadline:       form.deadline       || null,
      skills:         form.skills,
    })
  }

  return (
    <div className="max-w-3xl space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="page-title">Tạo tin tuyển dụng mới</h1>
          <p className="page-subtitle">Tin sẽ được lưu dưới dạng nháp, publish khi sẵn sàng</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Basic info */}
        <div className="glass-card p-6 space-y-5">
          <h2 className="section-title">Thông tin cơ bản</h2>

          <FieldGroup label="Vị trí tuyển dụng" icon={Briefcase} required>
            <input
              required
              value={form.position_title}
              onChange={set('position_title')}
              placeholder="Frontend Developer, Product Manager..."
              className="input-field"
            />
          </FieldGroup>

          <div className="grid sm:grid-cols-2 gap-4">
            <FieldGroup label="Địa điểm" icon={MapPin}>
              <input
                value={form.location}
                onChange={set('location')}
                placeholder="TP. Hồ Chí Minh, Hà Nội..."
                className="input-field"
              />
            </FieldGroup>

            <FieldGroup label="Loại công việc">
              <select value={form.job_type} onChange={set('job_type')} className="input-field">
                {JOB_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </FieldGroup>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <FieldGroup label="Lương tối thiểu (VND)" icon={DollarSign}>
              <input
                type="number"
                value={form.salary_min}
                onChange={set('salary_min')}
                placeholder="5000000"
                min={0}
                className="input-field"
              />
            </FieldGroup>

            <FieldGroup label="Lương tối đa (VND)" icon={DollarSign}>
              <input
                type="number"
                value={form.salary_max}
                onChange={set('salary_max')}
                placeholder="15000000"
                min={0}
                className="input-field"
              />
            </FieldGroup>
          </div>

          <FieldGroup label="Hạn nộp hồ sơ" icon={Calendar}>
            <input
              type="date"
              value={form.deadline}
              onChange={set('deadline')}
              className="input-field"
              min={new Date().toISOString().split('T')[0]}
            />
          </FieldGroup>
        </div>

        {/* Description */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="section-title">Mô tả công việc</h2>
          <textarea
            value={form.description}
            onChange={set('description')}
            rows={10}
            placeholder="Mô tả công việc, yêu cầu, quyền lợi...&#10;&#10;Ví dụ:&#10;**Yêu cầu:**&#10;- 2+ năm kinh nghiệm React&#10;- Biết TypeScript&#10;&#10;**Quyền lợi:**&#10;- Lương thưởng cạnh tranh&#10;- Bảo hiểm đầy đủ"
            className="input-field resize-none"
          />
        </div>

        {/* Skills */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="section-title flex items-center gap-2">
            <Tag size={16} className="text-brand-400" /> Kỹ năng yêu cầu
          </h2>
          <SkillInput
            skills={form.skills}
            onChange={(s) => setForm(p => ({ ...p, skills: s }))}
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            {mutation.isPending
              ? <Loader2 size={15} className="animate-spin" />
              : <Save size={15} />
            }
            Lưu nháp
          </button>
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            Hủy
          </button>
        </div>
      </form>
    </div>
  )
}
