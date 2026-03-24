import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, Trash2, Search, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { cvsApi } from '../api/cvs'

function CVCard({ cv, onDelete, onRecommend }) {
  return (
    <div className="glass-card p-4 flex items-center justify-between group hover:border-brand-500/30 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <p className="text-white text-sm font-medium truncate max-w-xs">{cv.filename}</p>
          <p className="text-slate-500 text-xs">
            {cv.file_size_kb ? `${cv.file_size_kb} KB` : ''} • {new Date(cv.uploaded_at).toLocaleDateString('vi-VN')}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={() => onRecommend(cv.id)} className="btn-secondary py-2 px-3 text-xs">
          <Search className="w-3 h-3" /> Tìm việc
        </button>
        <button onClick={() => onDelete(cv.id)} className="p-2 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-colors">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export default function UploadCVPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [uploadStatus, setUploadStatus] = useState(null)

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
    onSuccess: () => {
      setUploadStatus({ type: 'success', message: 'CV đã được upload thành công! Embedding đã được tạo.' })
      queryClient.invalidateQueries({ queryKey: ['cvs'] })
      setTimeout(() => setUploadStatus(null), 4000)
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
        <h2 className="text-2xl font-bold text-white">Upload CV</h2>
        <p className="text-slate-400 text-sm mt-1">Tải lên CV để AI phân tích và tìm việc làm phù hợp</p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
          ${isDragActive ? 'border-brand-500 bg-brand-500/10' : 'border-white/10 hover:border-brand-500/50 hover:bg-white/2'}`}
      >
        <input {...getInputProps()} />
        {uploadMutation.isPending ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-12 h-12 text-brand-400 animate-spin" />
            <p className="text-slate-300 font-medium">Đang xử lý CV và tạo embedding...</p>
            <p className="text-slate-500 text-sm">Quá trình này có thể mất 5-10 giây</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <Upload className={`w-8 h-8 ${isDragActive ? 'text-brand-400' : 'text-slate-500'}`} />
            </div>
            <div>
              <p className="text-white font-semibold">
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
            : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
          {uploadStatus.type === 'success' ? <CheckCircle className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
          {uploadStatus.message}
        </div>
      )}

      {/* CV List */}
      <div>
        <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-brand-400" />
          CV của bạn ({cvList?.total ?? 0})
        </h3>
        {listLoading ? (
          <div className="space-y-3">
            {[1,2].map(i => <div key={i} className="glass-card p-4 animate-pulse h-16 bg-dark-700/50" />)}
          </div>
        ) : cvList?.items?.length > 0 ? (
          <div className="space-y-3">
            {cvList.items.map(cv => (
              <CVCard
                key={cv.id}
                cv={cv}
                onDelete={(id) => deleteMutation.mutate(id)}
                onRecommend={(id) => navigate(`/recommend?cv_id=${id}`)}
              />
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
