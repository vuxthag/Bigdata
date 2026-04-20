import React, { useState } from 'react'
import {
  Brain, GraduationCap, Clock, TrendingUp,
  Lightbulb, ChevronDown, ChevronUp, AlertTriangle,
  BookOpen, CheckCircle2, Sparkles, Briefcase,
  Mail, Phone, Linkedin, Github, Award, Globe,
  FileText, Compass, Target, ArrowRight,
} from 'lucide-react'

/* ── Constants ────────────────────────────────── */
const EDU_LABELS = {
  high_school: 'THPT',
  associate:   'Cao đẳng',
  bachelor:    'Đại học',
  master:      'Thạc sĩ',
  phd:         'Tiến sĩ',
}

const SECTION_LABELS = {
  summary: 'Tóm tắt', education: 'Học vấn', experience: 'Kinh nghiệm',
  skills: 'Kỹ năng', certifications: 'Chứng chỉ', languages: 'Ngôn ngữ',
  interests: 'Sở thích', references: 'Tham chiếu',
}

/* ── Helpers ──────────────────────────────────── */
function capitalize(s) {
  if (!s) return 'Chưa xác định'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/* ── Reusable UI Components ──────────────────── */
function Panel({ children, className = '' }) {
  return (
    <div className={`bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden ${className}`}>
      {children}
    </div>
  )
}

function PanelHeader({ icon: Icon, iconColor = 'text-brand-500', title, badge }) {
  return (
    <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
      </div>
      {badge && <span className="text-[10px] font-semibold bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{badge}</span>}
    </div>
  )
}

function Tag({ label, variant = 'default' }) {
  const variants = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    brand:   'bg-brand-50 text-brand-600 border-brand-200',
    amber:   'bg-amber-50 text-amber-700 border-amber-200',
    rose:    'bg-rose-50 text-rose-600 border-rose-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    purple:  'bg-purple-50 text-purple-600 border-purple-200',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs border font-medium ${variants[variant]}`}>
      {label}
    </span>
  )
}

function StatBox({ icon: Icon, iconBg, iconColor, label, value }) {
  return (
    <div className="text-center">
      <div className={`w-9 h-9 rounded-xl ${iconBg} flex items-center justify-center mx-auto mb-1`}>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <p className="text-[10px] text-slate-500 leading-tight">{label}</p>
      <p className="text-xs font-semibold text-slate-800 mt-0.5">{value}</p>
    </div>
  )
}

function TipCard({ tip, index }) {
  const isPriority = index < 2
  return (
    <div className={`flex gap-3 p-3 rounded-xl border ${
      isPriority ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'
    }`}>
      <div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${
        isPriority ? 'bg-amber-400' : 'bg-slate-300'
      }`}>
        {isPriority
          ? <AlertTriangle className="w-2.5 h-2.5 text-white" />
          : <Lightbulb className="w-2.5 h-2.5 text-white" />
        }
      </div>
      <div>
        <p className={`text-xs leading-relaxed ${isPriority ? 'text-amber-800' : 'text-slate-700'}`}>{tip}</p>
        <span className={`mt-1 inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded ${
          isPriority ? 'bg-amber-200 text-amber-700' : 'bg-slate-200 text-slate-600'
        }`}>
          {isPriority ? '⚡ Ưu tiên cao' : '💡 Gợi ý'}
        </span>
      </div>
    </div>
  )
}

/* ── Section: Detected Sections Badge ─────────── */
function SectionsDetected({ sections }) {
  if (!sections || sections.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {sections.map(s => (
        <span key={s} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">
          <CheckCircle2 className="w-2.5 h-2.5" />
          {SECTION_LABELS[s] || s}
        </span>
      ))}
    </div>
  )
}

/* ── Section: Contact Info ────────────────────── */
function ContactInfo({ profile }) {
  const items = []
  if (profile.contact_email) items.push({ icon: Mail, text: profile.contact_email })
  if (profile.contact_phone) items.push({ icon: Phone, text: profile.contact_phone })
  if (profile.linkedin) items.push({ icon: Linkedin, text: profile.linkedin })
  if (profile.github) items.push({ icon: Github, text: profile.github })
  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
      {items.map((item, i) => (
        <span key={i} className="text-[11px] text-slate-500 flex items-center gap-1">
          <item.icon className="w-3 h-3 text-slate-400" />
          {item.text}
        </span>
      ))}
    </div>
  )
}

/* ── Section: Work Experience ─────────────────── */
function WorkExperienceSection({ experiences }) {
  const [showAll, setShowAll] = useState(false)
  if (!experiences || experiences.length === 0) return null
  const displayed = showAll ? experiences : experiences.slice(0, 3)

  return (
    <Panel>
      <PanelHeader icon={Briefcase} iconColor="text-blue-500" title="Kinh nghiệm làm việc" badge={`${experiences.length} vị trí`} />
      <div className="p-4 space-y-3">
        {displayed.map((exp, i) => (
          <div key={i} className="relative pl-4 border-l-2 border-blue-200">
            <div className="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-blue-400" />
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-slate-800">{exp.title || 'Vị trí chưa xác định'}</p>
                {exp.company && <p className="text-[11px] text-slate-500">{exp.company}</p>}
              </div>
              {exp.period && (
                <span className="text-[10px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full flex-shrink-0">{exp.period}</span>
              )}
            </div>
            {exp.description && (
              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed line-clamp-2">{exp.description}</p>
            )}
          </div>
        ))}
        {experiences.length > 3 && (
          <button onClick={() => setShowAll(!showAll)} className="text-brand-400 text-xs flex items-center gap-1 hover:text-brand-500">
            {showAll ? <><ChevronUp className="w-3 h-3" />Thu gọn</> : <><ChevronDown className="w-3 h-3" />Xem thêm {experiences.length - 3} vị trí</>}
          </button>
        )}
      </div>
    </Panel>
  )
}

/* ── Section: Education ───────────────────────── */
function EducationSection({ entries, level }) {
  if ((!entries || entries.length === 0) && !level) return null

  return (
    <Panel>
      <PanelHeader icon={GraduationCap} iconColor="text-indigo-500" title="Học vấn" />
      <div className="p-4 space-y-3">
        {level && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-slate-500">Trình độ cao nhất:</span>
            <Tag label={EDU_LABELS[level] || level} variant="brand" />
          </div>
        )}
        {entries && entries.map((edu, i) => (
          <div key={i} className="relative pl-4 border-l-2 border-indigo-200">
            <div className="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-indigo-400" />
            <p className="text-xs font-semibold text-slate-800">{edu.school || 'Trường chưa xác định'}</p>
            {edu.degree && <p className="text-[11px] text-slate-500">{edu.degree}</p>}
            {edu.period && <p className="text-[10px] text-slate-400">{edu.period}</p>}
            {edu.details && <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{edu.details}</p>}
          </div>
        ))}
      </div>
    </Panel>
  )
}

/* ── Section: Skills by Category ──────────────── */
function SkillsSection({ skillsByCategory, totalSkills }) {
  const [showAll, setShowAll] = useState(false)
  const categories = Object.entries(skillsByCategory || {})
  if (categories.length === 0 && totalSkills === 0) return null

  const displayed = showAll ? categories : categories.slice(0, 4)

  const categoryColors = {
    'Ngôn ngữ lập trình': 'brand',
    'Frontend': 'purple',
    'Backend': 'emerald',
    'Database': 'amber',
    'Cloud / DevOps': 'rose',
    'Data / AI / ML': 'brand',
    'Tools': 'default',
    'Methodology': 'purple',
    'Khác': 'default',
  }

  return (
    <Panel>
      <PanelHeader icon={Sparkles} iconColor="text-brand-500" title="Kỹ năng phát hiện" badge={`${totalSkills} kỹ năng`} />
      <div className="p-4 space-y-3">
        {displayed.map(([category, skills]) => (
          <div key={category}>
            <p className="text-[11px] font-semibold text-slate-600 mb-1.5">{category}</p>
            <div className="flex flex-wrap gap-1.5">
              {skills.map(s => <Tag key={s} label={s} variant={categoryColors[category] || 'default'} />)}
            </div>
          </div>
        ))}
        {categories.length > 4 && (
          <button onClick={() => setShowAll(!showAll)} className="text-brand-400 text-xs flex items-center gap-1 hover:text-brand-500">
            {showAll ? <><ChevronUp className="w-3 h-3" />Thu gọn</> : <><ChevronDown className="w-3 h-3" />Xem thêm {categories.length - 4} nhóm</>}
          </button>
        )}
        {categories.length === 0 && (
          <p className="text-xs text-slate-400 italic">AI chưa phát hiện kỹ năng rõ ràng trong CV.</p>
        )}
      </div>
    </Panel>
  )
}

/* ── Section: Career Directions ───────────────── */
function CareerDirectionsSection({ directions }) {
  if (!directions || directions.length === 0) return null

  return (
    <Panel>
      <PanelHeader icon={Compass} iconColor="text-purple-500" title="Định hướng nghề nghiệp" />
      <div className="p-4 space-y-3">
        <p className="text-xs text-slate-500 mb-1">
          Dựa trên kỹ năng trong CV, AI đề xuất các hướng đi phù hợp nhất:
        </p>
        {directions.map((dir, i) => {
          const pct = Math.round(dir.match_score * 100)
          const barColor = pct >= 30 ? 'bg-emerald-500' : pct >= 15 ? 'bg-amber-500' : 'bg-slate-300'
          return (
            <div key={i} className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className={`w-6 h-6 rounded-lg flex items-center justify-center text-white text-[10px] font-bold ${
                    i === 0 ? 'bg-gradient-to-br from-brand-500 to-purple-500' : 'bg-slate-400'
                  }`}>
                    {i + 1}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{dir.title}</p>
                    <p className="text-[10px] text-slate-500">{dir.description}</p>
                  </div>
                </div>
                <span className="text-xs font-bold text-slate-600 flex-shrink-0">{pct}%</span>
              </div>
              {/* Progress bar */}
              <div className="bg-slate-200 rounded-full h-1.5">
                <div className={`${barColor} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(pct * 2, 100)}%` }} />
              </div>
              {/* Skills */}
              <div className="flex flex-wrap gap-1">
                {dir.matched_skills?.slice(0, 5).map(s => (
                  <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-200">{s}</span>
                ))}
              </div>
              {dir.suggested_skills?.length > 0 && (
                <div className="mt-1">
                  <p className="text-[10px] text-slate-400 mb-1 flex items-center gap-1">
                    <Target className="w-2.5 h-2.5" /> Nên học thêm:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {dir.suggested_skills.slice(0, 4).map(s => (
                      <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

/* ── Section: Extra Info (Certs, Languages) ───── */
function ExtraInfoSection({ certifications, languages }) {
  if ((!certifications || certifications.length === 0) && (!languages || languages.length === 0)) return null

  return (
    <Panel>
      <PanelHeader icon={Award} iconColor="text-amber-500" title="Chứng chỉ & Ngôn ngữ" />
      <div className="p-4 space-y-3">
        {certifications?.length > 0 && (
          <div>
            <p className="text-[11px] font-semibold text-slate-600 mb-1.5 flex items-center gap-1">
              <Award className="w-3 h-3 text-amber-400" /> Chứng chỉ
            </p>
            <ul className="space-y-1">
              {certifications.map((c, i) => (
                <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
        {languages?.length > 0 && (
          <div>
            <p className="text-[11px] font-semibold text-slate-600 mb-1.5 flex items-center gap-1">
              <Globe className="w-3 h-3 text-blue-400" /> Ngôn ngữ
            </p>
            <div className="flex flex-wrap gap-1.5">
              {languages.map(l => <Tag key={l} label={l} variant="default" />)}
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function CVAnalysisPanel({ analysis }) {
  const [showAllTips, setShowAllTips] = useState(false)

  if (!analysis) return null

  const { cv_profile, improvement_tips = [], top_missing_skills = [] } = analysis
  const p = cv_profile || {}

  const tips = improvement_tips
  const displayedTips = showAllTips ? tips : tips.slice(0, 4)
  const hiddenTips = tips.length - 4

  return (
    <div className="space-y-4">

      {/* ─── 1. CV Overview ─── */}
      <Panel>
        <PanelHeader icon={Brain} iconColor="text-brand-500" title="Tổng quan CV" />
        <div className="p-4 space-y-4">

          {/* Summary */}
          {p.summary && (
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[11px] text-slate-500 font-semibold mb-1 flex items-center gap-1">
                <FileText className="w-3 h-3" /> Tóm tắt
              </p>
              <p className="text-xs text-slate-700 leading-relaxed line-clamp-4">{p.summary}</p>
            </div>
          )}

          {/* Contact */}
          <ContactInfo profile={p} />

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-3">
            <StatBox
              icon={GraduationCap}
              iconBg="bg-brand-50 border border-brand-100"
              iconColor="text-brand-500"
              label="Học vấn"
              value={EDU_LABELS[p.education_level] || 'Chưa rõ'}
            />
            <StatBox
              icon={Clock}
              iconBg="bg-purple-50 border border-purple-100"
              iconColor="text-purple-500"
              label="Kinh nghiệm"
              value={p.years_of_experience > 0 ? `${p.years_of_experience} năm` : 'Chưa rõ'}
            />
            <StatBox
              icon={TrendingUp}
              iconBg="bg-emerald-50 border border-emerald-100"
              iconColor="text-emerald-500"
              label="Cấp bậc"
              value={capitalize(p.detected_level)}
            />
          </div>

          {/* Sections detected */}
          <div>
            <p className="text-[10px] text-slate-500 mb-1">Các mục AI phát hiện trong CV:</p>
            <SectionsDetected sections={p.sections_found} />
          </div>
        </div>
      </Panel>

      {/* ─── 2. Education ─── */}
      <EducationSection entries={p.education_entries} level={p.education_level} />

      {/* ─── 3. Work Experience ─── */}
      <WorkExperienceSection experiences={p.work_experiences} />

      {/* ─── 4. Skills by Category ─── */}
      <SkillsSection skillsByCategory={p.skills_by_category} totalSkills={(p.skills || []).length} />

      {/* ─── 5. Extra Info ─── */}
      <ExtraInfoSection certifications={p.certifications} languages={p.languages} />

      {/* ─── 6. Career Directions ─── */}
      <CareerDirectionsSection directions={p.career_directions} />

      {/* ─── 7. Top Missing Skills ─── */}
      {top_missing_skills.length > 0 && (
        <Panel>
          <PanelHeader icon={BookOpen} iconColor="text-amber-500" title="Kỹ năng còn thiếu phổ biến" />
          <div className="p-4">
            <p className="text-xs text-slate-500 mb-3">
              Các kỹ năng được yêu cầu nhiều nhất trong các công việc phù hợp:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {top_missing_skills.map((s, i) => (
                <Tag key={s} label={s} variant={i < 3 ? 'rose' : 'amber'} />
              ))}
            </div>
          </div>
        </Panel>
      )}

      {/* ─── 8. Improvement Tips ─── */}
      {tips.length > 0 && (
        <Panel>
          <PanelHeader icon={Lightbulb} iconColor="text-amber-400" title="Gợi ý cải thiện CV" badge={`${tips.length} gợi ý`} />
          <div className="p-4 space-y-2.5">
            {displayedTips.map((tip, i) => (
              <TipCard key={i} tip={tip} index={i} />
            ))}
            {hiddenTips > 0 && !showAllTips && (
              <button onClick={() => setShowAllTips(true)} className="text-brand-400 text-xs flex items-center gap-1 hover:text-brand-500 mt-1">
                <ChevronDown className="w-3 h-3" />Xem thêm {hiddenTips} gợi ý
              </button>
            )}
            {showAllTips && hiddenTips > 0 && (
              <button onClick={() => setShowAllTips(false)} className="text-slate-400 text-xs flex items-center gap-1 hover:text-slate-600 mt-1">
                <ChevronUp className="w-3 h-3" />Thu gọn
              </button>
            )}
          </div>
        </Panel>
      )}
    </div>
  )
}
