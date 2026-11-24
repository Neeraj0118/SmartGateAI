import { apiClient } from './client'

export const createPermission = (key, payload) =>
  apiClient(key).post('/api/v1/hostel-permissions', payload)

export const listPermissions = (key, params = {}) =>
  apiClient(key).get('/api/v1/hostel-permissions', { params })

export const getPermission = (key, id) =>
  apiClient(key).get(`/api/v1/hostel-permissions/${id}`)

export const approvePermission = (key, id) =>
  apiClient(key).post(`/api/v1/hostel-permissions/${id}/approve`)

export const rejectPermission = (key, id, rejection_reason) =>
  apiClient(key).post(`/api/v1/hostel-permissions/${id}/reject`, { rejection_reason })

export const listActiveOutings = (key, params = {}) =>
  apiClient(key).get('/api/v1/hostel-permissions/outings/active', { params })

export const listSecurityAlerts = (key, params = {}) =>
  apiClient(key).get('/api/v1/hostel-permissions/alerts', { params })

export const resolveSecurityAlert = (key, alertId) =>
  apiClient(key).post(`/api/v1/hostel-permissions/alerts/${alertId}/resolve`)

export const getHostelStats = (key) =>
  apiClient(key).get('/api/v1/hostel-permissions/stats')
