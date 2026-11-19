import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const publicClient = axios.create({ baseURL: BASE, timeout: 10000 })

export const apiClient = (adminKey) =>
  axios.create({
    baseURL: BASE,
    timeout: 15000,
    headers: adminKey ? { 'X-Admin-API-Key': adminKey } : {},
  })

export const BASE_URL = BASE
export const STREAM_URL = `${BASE}/api/v1/camera/stream`
