'use client'
import { useEffect, useState } from 'react'
import { fetchHealth } from '@/lib/api'

export default function Header({ title }: { title: string }) {
  const [status, setStatus] = useState<'healthy' | 'degraded' | 'unhealthy' | 'loading'>('loading')

  useEffect(() => {
    fetchHealth()
      .then(h => setStatus(h.status as 'healthy' | 'degraded' | 'unhealthy'))
      .catch(() => setStatus('unhealthy'))
  }, [])

  const statusColor = {
    healthy: 'var(--green)',
    degraded: 'var(--yellow)',
    unhealthy: 'var(--red)',
    loading: 'var(--text-muted)',
  }[status]

  const statusLabel = {
    healthy: 'Online',
    degraded: 'Degraded',
    unhealthy: 'Offline',
    loading: '...',
  }[status]

  return (
    <header style={{
      height: 'var(--header-height)',
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <h1 style={{
        fontWeight: 700,
        fontSize: 16,
        color: 'var(--text-primary)',
        letterSpacing: '0.02em',
      }}>
        {title}
      </h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* API Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 7, height: 7,
            borderRadius: '50%',
            background: statusColor,
            boxShadow: status === 'healthy' ? `0 0 6px ${statusColor}` : 'none',
            animation: status === 'healthy' ? 'pulse-glow 2s ease infinite' : 'none',
          }} />
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            API {statusLabel}
          </span>
        </div>

        {/* Version badge */}
        <span style={{
          fontSize: 10,
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          padding: '2px 8px',
          borderRadius: 4,
        }}>
          v1.1.0
        </span>
      </div>
    </header>
  )
}
