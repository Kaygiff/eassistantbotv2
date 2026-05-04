import Cookies from 'js-cookie'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'eadmin_token'

export function getToken(): string | undefined {
  return Cookies.get(TOKEN_KEY)
}

export function setToken(token: string): void {
  Cookies.set(TOKEN_KEY, token, { expires: 365, sameSite: 'strict' })
}

export function removeToken(): void {
  Cookies.remove(TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

// Health
export const fetchHealth = () => api.get<{ status: string; services: Record<string, { status: string; latency_ms?: number }> }>('/health')

// Dashboard
export const fetchDashboard = () => api.get<{
  users_total: number
  users_banned: number
  groups_total: number
  transactions_total: number
}>('/api/v1/admin/dashboard')

// Users
export const fetchUsers = (params?: { limit?: number; offset?: number; search?: string; is_banned?: boolean }) => {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  if (params?.search) qs.set('search', params.search)
  if (params?.is_banned !== undefined) qs.set('is_banned', String(params.is_banned))
  const query = qs.toString()
  return api.get<User[]>(`/api/v1/users/${query ? `?${query}` : ''}`)
}
export const banUser = (id: string, reason?: string) =>
  api.post(`/api/v1/users/${id}/ban`, { reason })
export const unbanUser = (id: string) =>
  api.post(`/api/v1/users/${id}/unban`)

// Stats
export const fetchUserGrowth = (days = 30) =>
  api.get<{ created_at: string }[]>(`/api/v1/stats/users/growth?days=${days}`)
export const fetchEconomyVolume = (days = 7) =>
  api.get<{ type: string; amount: number; reason: string; created_at: string }[]>(`/api/v1/stats/economy/volume?days=${days}`)
export const fetchLanguageStats = () =>
  api.get<Record<string, number>>('/api/v1/stats/languages')
export const fetchCasinoStats = () =>
  api.get<{ total_rounds: number; total_bet: number; total_house_fee: number; wins: number; losses: number; by_game: Record<string, unknown> }>('/api/v1/casino/stats')

// Feature flags
export const fetchFlags = () => api.get<FeatureFlag[]>('/api/v1/flags/')
export const updateFlag = (name: string, enabled: boolean) =>
  api.put(`/api/v1/flags/${name}`, { enabled })

// Brain editor
export const fetchBrainStats = () => api.get<BrainStats>('/api/v1/brain/stats')
export const fetchBrainRules = () => api.get<BrainRule[]>('/api/v1/brain/rules')
export const updateBrainRule = (intent: string, keywords: string[]) =>
  api.put(`/api/v1/brain/rules/${intent}`, { keywords })
export const deleteBrainRule = (intent: string) =>
  api.delete(`/api/v1/brain/rules/${intent}`)
export const reloadBrainRules = () =>
  api.post('/api/v1/brain/rules/reload')

// Broadcast
export const sendBroadcast = (text: string, language?: string) =>
  api.post('/api/v1/notifications/broadcast', { text, language })

// Groups
export const fetchGroups = () => api.get<Group[]>('/api/v1/groups/')

// Types
export interface User {
  id: string
  telegram_id: number
  username?: string
  first_name?: string
  language: string
  assistant_name: string
  is_banned: boolean
  created_at: string
}

export interface FeatureFlag {
  name: string
  enabled: boolean
  description?: string
}

export interface BrainStats {
  total_intents: number
  total_keyword_rules: number
  custom_rules_count: number
  cache_active: boolean
}

export interface BrainRule {
  intent: string
  keywords: string[]
}

export interface Group {
  id: string
  chat_id: number
  title: string
  language: string
  warn_threshold: number
  created_at: string
}
