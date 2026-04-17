import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { cvsApi } from '../../api/cvs'

export default function CVSelector({ selectedCvId, onCvChange, cvList }) {
  const queryClient = useQueryClient()
  const [uploadStatus, setUploadStatus] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: (file) => {
      const fd = new FormData()
      fd.append('file', file)
      return cvsApi.upload(fd)
    },
    onSuccess: (res) => {
      setUploadStatus({ type: 'success', message: 'CV đã được upload thành công! Đang tự động chọn...' })
      queryClient.invalidateQueries({ queryKey: ['cvs'] })
      setTimeout(() => setUploadStatus(null), 4000)
      if (res?.data?.id) {
        onCvChange(res.data.id)
      }
    },
    onError: (err) => {
      setUploadStatus({ type: 'error', message: err.message || 'Upload thất bại' })
    },
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
    <div className="space-y-5">
      {/* Nơi upload CV mới */}
      <div
        {...getRootProps()}
        className={`border-slate-200 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200
          ${isDragActive ? 'border-brand-400 bg-brand-50' : 'border-slate-200 hover:border-brand-400 hover:bg-slate-50'}`}
      >
        <input {...getInputProps()} />
        {uploadMutation.isPending ? (
           <div className="flex flex-col items-center gap-2">
             <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
             <p className="text-slate-600 font-medium text-sm">Đang upload CV và tạo AI embedding...</p>
           </div>
        ) : (
           <div className="flex flex-col items-center gap-2">
             <div className="w-12 h-12 rounded-2xl bg-brand-50 border border-brand-100 flex items-center justify-center">
               <Upload className={`w-6 h-6 ${isDragActive ? 'text-brand-500' : 'text-slate-500'}`} />
             </div>
             <div>
               <p className="text-slate-800 font-semibold text-sm">
                 {isDragActive ? 'Thả file vào đây' : 'Kéo thả CV mới vào đây để phân tích ngay'}
               </p>
               <p className="text-slate-500 text-xs mt-1">hoặc click để chọn file • PDF / DOCX • Tối đa 10MB</p>
             </div>
           </div>
        )}
      </div>

      {uploadStatus && (
        <div className={`flex items-center gap-2 p-3 rounded-xl border text-xs font-medium
          ${uploadStatus.type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
            : 'bg-red-50 border-red-200 text-red-600'}`}>
          {uploadStatus.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {uploadStatus.message}
        </div>
      )}

      {/* Nơi chọn CV cũ */}
      <div className="pt-2 border-t border-slate-100">
        <label className="field-label text-sm text-slate-700 mb-2 block">
           {cvList?.items?.length > 0 ? "Hoặc chọn CV đã lưu trong hệ thống" : "Không có CV nào trong hệ thống"}
        </label>
        {cvList?.items?.length > 0 && (
          <select className="input-field py-2.5 text-sm" value={selectedCvId} onChange={e => onCvChange(e.target.value)}>
            <option value="">-- Chọn CV --</option>
            {cvList.items.map(cv => (
              <option key={cv.id} value={cv.id}>{cv.filename}</option>
            ))}
          </select>
        )}
      </div>
    </div>
  )
}
