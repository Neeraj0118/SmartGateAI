import { apiClient, publicClient } from './client'

// GET /api/v1/students — returns { total, items, skip, limit }
export const listStudents = (key, params = {}) =>
  apiClient(key).get('/api/v1/students', { params })

export const getStudent = (key, studentId) =>
  apiClient(key).get(`/api/v1/students/${encodeURIComponent(studentId)}`)

export const registerStudent = (key, formData) =>
  apiClient(key).post('/api/v1/students', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })

export const updateStudent = (key, studentId, payload) =>
  apiClient(key).put(`/api/v1/students/${encodeURIComponent(studentId)}`, payload)

export const deleteStudent = (key, studentId) =>
  apiClient(key).delete(`/api/v1/students/${encodeURIComponent(studentId)}`)

export const addPhoto = (key, studentId, formData) =>
  apiClient(key).post(`/api/v1/students/${encodeURIComponent(studentId)}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
