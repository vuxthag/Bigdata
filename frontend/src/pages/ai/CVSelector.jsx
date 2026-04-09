import React from 'react'

export default function CVSelector({ activeTab, selectedCvId, onCvChange, cvList, selectedJobId, onJobChange, jobList, jobTitle, onJobTitleChange, onKeyDown }) {
  if (activeTab === 'cv') {
    return (
      <div>
        <label className="field-label">Chọn CV</label>
        <select className="input-field" value={selectedCvId} onChange={e => onCvChange(e.target.value)}>
          <option value="">-- Chọn CV --</option>
          {cvList?.items?.map(cv => (
            <option key={cv.id} value={cv.id}>{cv.filename}</option>
          ))}
        </select>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="field-label">Chọn vị trí có sẵn</label>
        <select className="input-field" value={selectedJobId} onChange={e => onJobChange(e.target.value)}>
          <option value="">-- Chọn vị trí --</option>
          {jobList?.items?.slice(0, 50).map(j => (
            <option key={j.id} value={j.position_title}>{j.position_title}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="field-label">Hoặc nhập chức danh</label>
        <input
          className="input-field"
          placeholder="VD: Data Scientist, Software Engineer..."
          value={jobTitle}
          onChange={e => onJobTitleChange(e.target.value)}
          onKeyDown={onKeyDown}
        />
      </div>
    </div>
  )
}
