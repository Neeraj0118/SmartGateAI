import { publicClient } from './client'

export const getHealth = () => publicClient.get('/health')
export const getApiHealth = () => publicClient.get('/api/v1/health')
