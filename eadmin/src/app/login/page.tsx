'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { setToken } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [token, setTokenInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token.trim()) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/dashboard`, {
        headers: { Authorization: `Bearer ${token.trim()}` },
      })
      if (res.ok) {
        setToken(token.trim())
        router.push('/dashboard')
      } else {
        setError('Неверный токен. Проверь и попробуй снова.')
      }
    } catch {
      setError('Не удалось подключиться к API.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-base)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        width: 400, height: 400,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(78,205,196,0.06) 0%, transparent 70%)',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        width: '100%',
        maxWidth: 400,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)',
        padding: '40px 36px',
        animation: 'fadeIn 0.4s ease',
        position: 'relative',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img
            src="/logo-dark.png"
            alt="E'assistant"
            style={{ width: 72, height: 72, objectFit: 'contain', marginBottom: 16 }}
          />
          <h1 style={{
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: '0.04em',
            color: 'var(--text-primary)',
          }}>
            E<span style={{ color: 'var(--accent)' }}>'</span>ADMIN
          </h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
            Панель управления платформой
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              JWT Токен
            </label>
            <textarea
              value={token}
              onChange={e => setTokenInput(e.target.value)}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              rows={3}
              style={{
                width: '100%',
                background: 'var(--bg-elevated)',
                border: `1px solid ${error ? 'var(--red)' : 'var(--border)'}`,
                borderRadius: 'var(--radius)',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                resize: 'none',
                outline: 'none',
                lineHeight: 1.5,
                transition: 'border-color 0.15s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = error ? 'var(--red)' : 'var(--border)')}
            />
          </div>

          {error && (
            <p style={{ fontSize: 12, color: 'var(--red)', padding: '8px 12px', background: 'var(--red-dim)', borderRadius: 'var(--radius)' }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !token.trim()}
            style={{
              width: '100%',
              padding: '12px',
              background: loading || !token.trim() ? 'var(--bg-elevated)' : 'var(--accent)',
              color: loading || !token.trim() ? 'var(--text-muted)' : 'var(--bg-base)',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 14,
              cursor: loading || !token.trim() ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
              letterSpacing: '0.05em',
            }}
          >
            {loading ? 'Проверка...' : 'Войти'}
          </button>
        </form>

        <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 20 }}>
          Получи токен: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>python scripts/create_admin_token.py</code>
        </p>
      </div>
    </div>
  )
}
