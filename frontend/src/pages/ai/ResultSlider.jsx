import React from 'react'

export default function ResultSlider({ topN, onChange }) {
  return (
    <div>
      <label className="field-label">
        Số kết quả: <span className="text-brand-400 font-semibold">{topN}</span>
      </label>
      <input
        type="range"
        min={3}
        max={15}
        value={topN}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-brand-500 h-2 rounded-full"
      />
      <div className="flex justify-between text-xs text-slate-600 mt-1">
        <span>3</span>
        <span>15</span>
      </div>
    </div>
  )
}
