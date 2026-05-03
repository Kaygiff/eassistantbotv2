'use client'
import { useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { api } from '@/lib/api'
import { Shield, Search, AlertTriangle, Ban, CheckCircle } from 'lucide-react'

export default function ModerationPage() {
  const [userId, setUserId] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null)

  const showResult = (msg: string, type: 'ok' | 'err') => {
    setResult({ msg, type })
    setTimeout(() => setResult(null), 3500)
  }

  const doAction = async (action: 'ban' | 'unban') => {
    if (!userId.trim()) return
    setLoading(true)
    try {
      if (action === 'ban') {
        await api.post(`/api/v1/users/${userId.trim()}/ban`, { reason: reason || 'Admin action' })
        showResult('Пользователь заблокирован', 'ok')
      } else {
        await api.post(`/api/v1/users/${userId.trim()}/unban`)
        showResult('Пользователь разблокирован', 'ok')
      }
      setUserId('')
      setReason('')
    } catch {
      showResult('Ошибка. Проверь UUID пользователя.', 'err')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AdminLayout title="Модерация">
      <div style={{ maxWidth: 600, display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Info */}
        <div style={{ display: 'flex', gap: 12, padding: '14px 18px', borderRadius: 'var(--radius-lg)', background: 'var(--accent-dim)', border: '1px solid var(--accent)' }}>
          <Shield size={16} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: 13, color: 'var(--accent)', lineHeight: 1.5 }}>
            Используй UUID пользователя из раздела Пользователи. Бан применяется немедленно — при следующем сообщении бот его отклонит.
          </p>
        </div>

        {/* Quick action form */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Быстрое действие</h2>

          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              UUID пользователя
            </label>
            <input
              value={userId}
              onChange={e => setUserId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              style={{
                width: '100%', padding: '10px 14px',
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', color: 'var(--text-primary)',
                fontSize: 12, fontFamily: 'var(--font-mono)', outline: 'none',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              Причина (опционально)
            </label>
            <input
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Нарушение правил, спам..."
              style={{
                width: '100%', padding: '10px 14px',
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', color: 'var(--text-primary)',
                fontSize: 13, fontFamily: 'var(--font-display)', outline: 'none',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={() => doAction('ban')}
              disabled={loading || !userId.trim()}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                padding: '11px', background: !userId.trim() ? 'var(--bg-elevated)' : 'var(--red-dim)',
                border: `1px solid ${!userId.trim() ? 'var(--border)' : 'var(--red)'}`,
                color: !userId.trim() ? 'var(--text-muted)' : 'var(--red)',
                borderRadius: 'var(--radius)', fontFamily: 'var(--font-display)',
                fontWeight: 700, fontSize: 13, cursor: !userId.trim() ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              <Ban size={14} /> Заблокировать
            </button>
            <button
              onClick={() => doAction('unban')}
              disabled={loading || !userId.trim()}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                padding: '11px', background: !userId.trim() ? 'var(--bg-elevated)' : 'var(--green-dim)',
                border: `1px solid ${!userId.trim() ? 'var(--border)' : 'var(--green)'}`,
                color: !userId.trim() ? 'var(--text-muted)' : 'var(--green)',
                borderRadius: 'var(--radius)', fontFamily: 'var(--font-display)',
                fontWeight: 700, fontSize: 13, cursor: !userId.trim() ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              <CheckCircle size={14} /> Разблокировать
            </button>
          </div>

          {result && (
            <div style={{
              padding: '10px 14px', borderRadius: 'var(--radius)',
              background: result.type === 'ok' ? 'var(--green-dim)' : 'var(--red-dim)',
              border: `1px solid ${result.type === 'ok' ? 'var(--green)' : 'var(--red)'}`,
              color: result.type === 'ok' ? 'var(--green)' : 'var(--red)',
              fontSize: 13, fontWeight: 600, animation: 'fadeIn 0.2s ease',
            }}>
              {result.msg}
            </div>
          )}
        </div>

        {/* Go to users */}
        <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>
          Для поиска пользователей и массовых действий используй раздел{' '}
          <a href="/users" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Пользователи →</a>
        </div>
      </div>
    </AdminLayout>
  )
}
