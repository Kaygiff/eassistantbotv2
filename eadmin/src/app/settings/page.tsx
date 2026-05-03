'use client'
import AdminLayout from '@/components/AdminLayout'
import { Settings, ExternalLink } from 'lucide-react'

const LINKS = [
  { label: 'Supabase Dashboard', url: 'https://app.supabase.com', desc: 'БД, Storage, Auth' },
  { label: 'Railway', url: 'https://railway.app', desc: 'Деплой сервисов' },
  { label: 'Flower (Celery)', url: 'http://localhost:5555', desc: 'Мониторинг очередей' },
  { label: 'API Docs', url: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/docs`, desc: 'FastAPI Swagger' },
  { label: 'Sentry', url: 'https://sentry.io', desc: 'Мониторинг ошибок' },
]

export default function SettingsPage() {
  return (
    <AdminLayout title="Настройки">
      <div style={{ maxWidth: 680, display: 'flex', flexDirection: 'column', gap: 28 }}>

        {/* Version info */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
            <img src="/logo-light.svg" alt="Logo" style={{ width: 48, height: 48, objectFit: 'contain' }} />
            <div>
              <h2 style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>
                E<span style={{ color: 'var(--accent)' }}>'</span>ASSISTANT
              </h2>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v1.1.0 · EAdmin Panel</p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Platform', value: 'Next.js 14 + FastAPI' },
              { label: 'Database', value: 'Supabase (PostgreSQL)' },
              { label: 'Queue', value: 'Celery + Redis' },
              { label: 'AI', value: 'GPT-4o + 7 fallbacks' },
            ].map(({ label, value }) => (
              <div key={label} style={{ padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick links */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 16, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Внешние сервисы
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {LINKS.map(({ label, url, desc }) => (
              <a key={label} href={url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 16px', borderRadius: 'var(--radius)',
                  background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                  transition: 'border-color 0.15s, background 0.15s', cursor: 'pointer',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-strong)'
                  ;(e.currentTarget as HTMLDivElement).style.background = 'var(--bg-hover)'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'
                  ;(e.currentTarget as HTMLDivElement).style.background = 'var(--bg-elevated)'
                }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{desc}</div>
                  </div>
                  <ExternalLink size={13} color="var(--text-muted)" />
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Scripts */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 16, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Полезные скрипты
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { cmd: 'python scripts/check_env.py', desc: 'Проверка переменных окружения' },
              { cmd: 'python scripts/migrate.py', desc: 'Применить SQL миграции' },
              { cmd: 'python scripts/seed_db.py', desc: 'Заполнить тестовыми данными' },
              { cmd: 'python scripts/create_admin_token.py', desc: 'Создать JWT токен для EAdmin' },
              { cmd: 'pytest tests/ -v', desc: 'Запустить тесты' },
            ].map(({ cmd, desc }) => (
              <div key={cmd} style={{ padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                <code style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{cmd}</code>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminLayout>
  )
}
