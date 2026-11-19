import { apiClient } from './client'

// GET /api/v1/vehicles/ => { total, items, skip, limit }
export const listVehicles = (key, params = {}) =>
  apiClient(key).get('/api/v1/vehicles/', { params })

// POST /api/v1/vehicles/ => VehicleResponse
export const registerVehicle = (key, payload) =>
  apiClient(key).post('/api/v1/vehicles/', payload)

// PUT /api/v1/vehicles/:id => VehicleResponse
export const updateVehicle = (key, id, payload) =>
  apiClient(key).put(`/api/v1/vehicles/${id}`, payload)

// DELETE /api/v1/vehicles/:id => 204
export const deleteVehicle = (key, id) =>
  apiClient(key).delete(`/api/v1/vehicles/${id}`)
