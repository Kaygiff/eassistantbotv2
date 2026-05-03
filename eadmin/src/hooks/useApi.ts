/**
 * useApi.ts — SWR-based hooks для всех API endpoint'ов EAdmin.
 * Автоматическая повторная выборка, кэширование, состояния загрузки.
 */

import useSWR, { SWRConfiguration } from 'swr'
import { api } from '@/lib/api'

// Базовый fetcher для SWR
const fetcher = (url: string) => api.get(url)

const DEFAULT_CONFIG: SWRConfiguration = {
  refreshInterval: 30_000,   // обновляем каждые 30 сек
  revalidateOnFocus: true,
  dedupingInterval: 5_000,
}

// --- Dashboard ---
export function useDashboard() {
  return useSWR('/api/v1/admin/dashboard', fetcher, DEFAULT_CONFIG)
}

// --- Users ---
export function useUsers(params?: { search?: string; is_banned?: boolean; limit?: number }) {
  const qs = params
    ? '?' + new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
      ).toString()
    : ''
  return useSWR(`/api/v1/users/${qs}`, fetcher, DEFAULT_CONFIG)
}

// --- Stats ---
export function useUserGrowth(days = 30) {
  return useSWR(`/api/v1/stats/users/growth?days=${days}`, fetcher, DEFAULT_CONFIG)
}

export function useEconomyVolume(days = 7) {
  return useSWR(`/api/v1/stats/economy/volume?days=${days}`, fetcher, DEFAULT_CONFIG)
}

export function useLanguageStats() {
  return useSWR('/api/v1/stats/languages', fetcher, { ...DEFAULT_CONFIG, refreshInterval: 60_000 })
}

// --- Casino ---
export function useCasinoStats() {
  return useSWR('/api/v1/casino/stats', fetcher, DEFAULT_CONFIG)
}

export function useCasinoRounds(params?: { game_type?: string; limit?: number }) {
  const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
  return useSWR(`/api/v1/casino/rounds${qs}`, fetcher, DEFAULT_CONFIG)
}

// --- Feature Flags ---
export function useFlags() {
  return useSWR('/api/v1/flags/', fetcher, { ...DEFAULT_CONFIG, refreshInterval: 10_000 })
}

// --- Brain ---
export function useBrainStats() {
  return useSWR('/api/v1/brain/stats', fetcher, DEFAULT_CONFIG)
}

export function useBrainRules() {
  return useSWR('/api/v1/brain/rules', fetcher, DEFAULT_CONFIG)
}

// --- Groups ---
export function useGroups() {
  return useSWR('/api/v1/groups/', fetcher, DEFAULT_CONFIG)
}

// --- Health ---
export function useHealth() {
  return useSWR('/health', fetcher, {
    refreshInterval: 15_000,
    revalidateOnFocus: true,
  })
}
