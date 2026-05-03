'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { fetchFlags, updateFlag, FeatureFlag } from '@/lib/api'
import { Zap, RefreshCw } from 'lucide-react'

export default function FlagsPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    fetchFlags().then(setFlags).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 2500) }

  const toggle = async (flag: FeatureFlag) => {
    setUpdating(flag.name)
    try {
      await updateFlag(flag.name, !flag.enabled)
      setFlags(prev => prev.map(f => f.name === flag.name ? { ...f, enabled: !f.enabled } : f))
      showToast(`${flag.name}: ${!flag.enabled ? 'включён' : 'выключен'}`)
    } catch {
      showToast('Ошибка обновления')
    } finally {
      setUpdating(null)
    }
  }

  return (
    <AdminLayout title="Feature Flags">
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 999,
          padding: '10px 16px', borderRadius: 'var(--radius)',
          background: 'var(--accent-dim)', border: '1px solid var(--accent)',
          color: 'var(--accent)', fontSize: 13, fontWeight: 600, animation: 'fadeIn 0.2s ease',
          fontFamily: 'var(--font-mono)',
        }}>{toast}</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Включай и выключай функции без перезапуска сервисов.
          </p>
          <button onClick={load} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
            background: 'var(--bg-surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-secondary)',
            fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-display)',
          }}>
            <RefreshCw size={12} /> Обновить
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка...</div>
        ) : flags.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: 60,
            background: 'var(--bg-surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)', color: 'var(--text-muted)',
          }}>
            <Zap size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
            <p>Флаги не найдены. Добавь их в таблицу feature_flags в Supabase.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {flags.map(flag => (
              <div key={flag.name} style={{
                display: 'flex', alignItems: 'center',
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)', padding: '16px 20px',
                transition: 'border-color 0.15s',
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <code style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-primary)', fontWeight: 600 }}>
                      {flag.name}
                    </code>
                    <span style={{
                      fontSize: 9, padding: '2px 7px', borderRadius: 3, fontWeight: 700, letterSpacing: '0.08em',
                      background: flag.enabled ? 'var(--green-dim)' : 'var(--red-dim)',
                      color: flag.enabled ? 'var(--green)' : 'var(--red)',
                    }}>
                      {flag.enabled ? 'ON' : 'OFF'}
                    </span>
                  </div>
                  {flag.description && (
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{flag.description}</p>
                  )}
                </div>

                {/* Toggle switch */}
                <button
                  onClick={() => toggle(flag)}
                  disabled={updating === flag.name}
                  style={{
                    width: 44, height: 24, borderRadius: 12,
                    background: flag.enabled ? 'var(--accent)' : 'var(--bg-elevated)',
                    border: `1px solid ${flag.enabled ? 'var(--accent)' : 'var(--border)'}`,
                    cursor: 'pointer', position: 'relative', transition: 'all 0.2s',
                    opacity: updating === flag.name ? 0.6 : 1,
                  }}
                >
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%',
                    background: flag.enabled ? 'var(--bg-base)' : 'var(--text-muted)',
                    position: 'absolute', top: 3,
                    left: flag.enabled ? 22 : 3,
                    transition: 'left 0.2s',
                  }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  )
}
