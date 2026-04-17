import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileText, Trash2, Search, Loader2, CheckCircle, AlertCircle,
  Brain, Tag, Target, BarChart3, Star, Zap, ChevronDown, ChevronUp,
} from 'lucide-react'
import { cvsApi } from '../api/cvs'

/* ── Mock skill extraction from filename / text ── */
function guessSkillsFromName(filename) {
  if (!filename) return []
  const lc = filename.toLowerCase()
  const matches = []
  const skillMap = {
    'python': 'Python', 'java': 'Java', 'react': 'React', 'node': 'Node.js',
    'data': 'Data Science', 'ml': 'Machine Learning', 'ai': 'AI/ML',
    'web': 'Web Dev', 'frontend': 'Frontend', 'backend': 'Backend',
    'devops': 'DevOps', 'cloud': 'Cloud', 'sql': 'SQL', 'docker': 'Docker',
    'angular': 'Angular', 'vue': 'Vue.js', 'fullstack': 'Full Stack',
  }
  Object.entries(skillMap).forEach(([key, val]) => {
    if (lc.includes(key)) matches.push(val)
  })
  // Always return some default skills if nothing matched
  if (matches.length === 0) return ['Communication', 'Teamwork', 'Problem Solving']
  return matches
}

function CVCard({ cv, onDelete, onRecommend }) {
  return (
    <div className="glass-card p-4 flex items-center justify-between group hover:border-slate-200rand-500/30 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-50rand-500/10 border border-slate-200rand-500/20 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <p className="text-slate-900 text-sm font-medium truncate max-w-xs">{cv.filename}</p>
          <p className="text-slate-500 text-xs">
            {cv.file_size_kb ? `${cv.file_size_kb} KB` : ''} • {new Date(cv.uploaded_at).toLocaleDateString('vi-VN')}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={() => onRecommend(cv.id)} className="btn-secondary py-2 px-3 text-xs">
          <Search className="w-3 h-3" /> Tìm việc
        </button>
        <button onClick={() => onDelete(cv.id)} className="p-2 rounded-lg hover:bg-slate-50ed-500/10 text-slate-500 hover:text-red-400 transition-colors">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

/* ── CV Analysis Panel ──────────────────────── */
function CVAnalysis({ cv }) {
  const [expanded, setExpanded] = useState(false)
  const skills = guessSkillsFromName(cv.filename)
  const fitScore = Math.floor(Math.random() * 30) + 65 // 65-95% mock

  return (
    <div className="glass-card p-5 border-slate-200rand-500/20 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-slate-900 font-semibold text-sm flex items-center gap-2">
          <Brain className="w-4 h-4 text-brand-400" />
          Phân tích CV: {cv.filename}
        </h4>
        <button onClick={() => setExpanded(!expanded)} className="text-slate-500 hover:text-slate-900 transition-colors">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Skills detected */}
      <div className="mb-4">
        <p className="text-slate-500 text-xs mb-2 flex items-center gap-1">
          <Tag className="w-3 h-3" /> Kỹ năng phát hiện
        </p>
        <div className="flex flex-wrap gap-1.5">
          {skills.map(s => (
            <span key={s} className="badge-brand text-xs">{s}</span>
          ))}
        </div>
      </div>

      {/* Fit score */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-slate-500 text-xs flex items-center gap-1">
            <Target className="w-3 h-3" /> Điểm phù hợp thị trường
          </p>
          <span className={`text-sm font-bold ${fitScore >= 80 ? 'text-emerald-400' : fitScore >= 60 ? 'text-amber-400' : 'text-slate-500'}`}>
            {fitScore}%
          </span>
        </div>
        <div className="w-full h-2 bg-white rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${fitScore >= 80 ? 'bg-emerald-500' : fitScore >= 60 ? 'bg-slate-50mber-500' : 'bg-slate-500'}`}
            style={{ width: `${fitScore}%` }}
          />
        </div>
      </div>

      {expanded && (
        <div className="space-y-3 animate-slide-down">
          {/* Experience level */}
          <div className="flex items-center gap-3">
            <BarChart3 className="w-4 h-4 text-brand-400" />
            <div>
              <p className="text-slate-500 text-xs">Mức kinh nghiệm ước tính</p>
              <p className="text-slate-900 text-sm font-medium">Junior – Mid Level</p>
            </div>
          </div>

          {/* Recommended categories */}
          <div>
            <p className="text-slate-500 text-xs mb-2 flex items-center gap-1">
              <Star className="w-3 h-3" /> Ngành nghề gợi ý
            </p>
            <div className="flex flex-wrap gap-1.5">
              {['Công nghệ thông tin', 'Data & AI', 'Phần mềm'].map(c => (
                <span key={c} className="tag">{c}</span>
              ))}
            </div>
          </div>

          {/* AI suggestion */}
          <div className="bg-slate-50rand-500/5 border border-slate-200rand-500/20 rounded-xl p-3 mt-2">
            <p className="text-brand-400 text-xs flex items-center gap-1 mb-1">
              <Zap className="w-3 h-3" /> Gợi ý AI
            </p>
            <p className="text-slate-600 text-xs leading-relaxed">
              CV của bạn có tiềm năng tốt. Hãy bổ sung thêm các dự án thực tế và chứng chỉ để tăng điểm phù hợp.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Main Component ──────────────────────────── */
export default function UploadCVPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [uploadStatus, setUploadStatus] = useState(null)
  const [lastUploadedCv, setLastUploadedCv] = useState(null)

  const { data: cvList, isLoading: listLoading } = useQuery({
    queryKey: ['cvs'],
    queryFn: () => cvsApi.list().then(r => r.data),
  })

  const uploadMutation = useMutation({
    mutationFn: (file) => {
      const fd = new FormData()
      fd.append('file', file)
      return cvsApi.upload(fd)
    },
    onSuccess: (res) => {
      setUploadStatus({ type: 'success', message: 'CV đã được upload thành công! Embedding đã được tạo.' })
      setLastUploadedCv(res?.data || { filename: 'uploaded-cv.pdf' })
      queryClient.invalidateQueries({ queryKey: ['cvs'] })
      setTimeout(() => setUploadStatus(null), 6000)
    },
    onError: (err) => {
      setUploadStatus({ type: 'error', message: err.message || 'Upload thất bại' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (cvId) => cvsApi.delete(cvId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cvs'] }),
  })

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setUploadStatus(null)
      setLastUploadedCv(null)
      uploadMutation.mutate(acceptedFiles[0])
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Upload CV</h2>
        <p className="text-slate-500 text-sm mt-1">Tải lên CV để AI phân tích và tìm việc làm phù hợp</p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-slate-200 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
          ${isDragActive ? 'border-slate-200rand-500 bg-slate-50rand-500/10' : 'border-slate-200 hover:border-slate-200rand-500/50 hover:bg-white/2'}`}
      >
        <input {...getInputProps()} />
        {uploadMutation.isPending ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-12 h-12 text-brand-400 animate-spin" />
            <p className="text-slate-600 font-medium">Đang xử lý CV và tạo embedding...</p>
            <p className="text-slate-500 text-sm">Quá trình này có thể mất 5-10 giây</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-slate-50rand-500/10 border border-slate-200rand-500/20 flex items-center justify-center">
              <Upload className={`w-8 h-8 ${isDragActive ? 'text-brand-400' : 'text-slate-500'}`} />
            </div>
            <div>
              <p className="text-slate-900 font-semibold">
                {isDragActive ? 'Thả file vào đây' : 'Kéo thả CV vào đây'}
              </p>
              <p className="text-slate-500 text-sm mt-1">hoặc click để chọn file • PDF / DOCX • Tối đa 10MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Status feedback */}
      {uploadStatus && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border text-sm
          ${uploadStatus.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
            : 'bg-slate-50ed-500/10 border-slate-200ed-500/30 text-red-400'}`}>
          {uploadStatus.type === 'success' ? <CheckCircle className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
          {uploadStatus.message}
        </div>
      )}

      {/* ── CV Analysis Section (after upload) ── */}
      {lastUploadedCv && (
        <CVAnalysis cv={lastUploadedCv} />
      )}

      {/* CV List */}
      <div>
        <h3 className="text-slate-900 font-semibold mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-brand-400" />
          CV của bạn ({cvList?.total ?? 0})
        </h3>
        {listLoading ? (
          <div className="space-y-3">
            {[1,2].map(i => <div key={i} className="glass-card p-4 animate-pulse h-16 bg-slate-1000" />)}
          </div>
        ) : cvList?.items?.length > 0 ? (
          <div className="space-y-3">
            {cvList.items.map(cv => (
              <div key={cv.id}>
                <CVCard
                  cv={cv}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onRecommend={(id) => navigate(`/recommend?cv_id=${id}`)}
                />
                {/* Show analysis for each existing CV */}
                <div className="mt-2">
                  <CVAnalysis cv={cv} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="glass-card p-8 text-center text-slate-500">
            <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">Chưa có CV nào. Hãy upload CV đầu tiên!</p>
          </div>
        )}
      </div>
    </div>
  )
}
