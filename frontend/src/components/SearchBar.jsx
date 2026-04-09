import React, { useState } from 'react'
import { Search, MapPin, Filter } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function SearchBar({
  onSearch,
  initialKeyword = '',
  initialLocation = '',
  showLocationField = true,
  className = '',
  compact = false,
}) {
  const [keyword, setKeyword] = useState(initialKeyword)
  const [location, setLocation] = useState(initialLocation)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e?.preventDefault?.()
    if (onSearch) {
      onSearch({ keyword, location })
    } else {
      const params = new URLSearchParams()
      if (keyword) params.set('q', keyword)
      if (location) params.set('loc', location)
      navigate(`/jobs?${params.toString()}`)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`glass-card ${compact ? 'p-2' : 'p-3'} flex flex-col sm:flex-row gap-2 ${className}`}
    >
      {/* Keyword */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          className="search-input pl-10"
          placeholder="Chức danh, kỹ năng, từ khóa..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </div>

      {/* Location */}
      {showLocationField && (
        <div className="relative sm:w-52">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            className="search-input pl-10"
            placeholder="Địa điểm..."
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
      )}

      {/* Search button */}
      <button type="submit" className="btn-accent py-3 px-6 flex-shrink-0">
        <Search className="w-4 h-4" />
        Tìm kiếm
      </button>
    </form>
  )
}
