import { apiClient, publicClient, BASE_URL } from './client'

// GET /api/v1/attendance/ → { total, items, skip, limit }
export const listAttendance = (key, params = {}) =>
  apiClient(key).get('/api/v1/attendance/', { params })

// GET /api/v1/attendance/stats → { total_today, known_today, unknown_today, unique_students_today }
export const getAttendanceStats = (key) =>
  apiClient(key).get('/api/v1/attendance/stats')

// GET /api/v1/attendance/export/csv — download CSV
export const getAttendanceCsvUrl = (key, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return `${BASE_URL}/api/v1/attendance/export/csv${qs ? '?' + qs : ''}`
}

export const exportAttendanceCsv = (key, params = {}) =>
  apiClient(key).get('/api/v1/attendance/export/csv', {
    params,
    responseType: 'blob',
  })
