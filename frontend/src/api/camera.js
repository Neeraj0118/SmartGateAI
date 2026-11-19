import { apiClient, publicClient } from './client'

// POST /api/v1/camera/start?gate_mode=entry  (admin)
export const startCamera = (key, gateMode = 'entry') =>
  apiClient(key).post(`/api/v1/camera/start?gate_mode=${gateMode}`)

// POST /api/v1/camera/stop  (admin)
export const stopCamera = (key) => apiClient(key).post('/api/v1/camera/stop')

// GET /api/v1/camera/status  (public) — { running, fps, faces_detected, known_count, unknown_count, gate_mode, results }
export const getCameraStatus = () => publicClient.get('/api/v1/camera/status')

// GET /api/v1/camera/mode  (public) — { gate_mode, running }
export const getCameraMode = () => publicClient.get('/api/v1/camera/mode')

// POST /api/v1/camera/mode?gate_mode=entry  (admin)
export const setCameraMode = (key, mode) =>
  apiClient(key).post(`/api/v1/camera/mode?gate_mode=${mode}`)

// POST /api/v1/camera/reload-embeddings  (admin)
export const reloadEmbeddings = (key) => apiClient(key).post('/api/v1/camera/reload-embeddings')
