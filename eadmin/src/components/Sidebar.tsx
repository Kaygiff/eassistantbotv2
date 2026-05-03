'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Users, BarChart3, Zap, Brain,
  MessageSquare, Shield, Settings, LogOut, ServerCrash, Users2
} from 'lucide-react'
import { removeToken } from '@/lib/api'

const NAV = [
  { href: '/dashboard',     icon: LayoutDashboard, label: 'Дашборд' },
  { href: '/users',         icon: Users,            label: 'Пользователи' },
  { href: '/groups',        icon: Users2,           label: 'Группы' },
  { href: '/stats',         icon: BarChart3,        label: 'Аналитика' },
  { href: '/casino',        icon: ServerCrash,      label: 'Казино' },
  { href: '/flags',         icon: Zap,              label: 'Feature Flags' },
  { href: '/brain',         icon: Brain,            label: 'Brain Editor' },
  { href: '/broadcast',     icon: MessageSquare,    label: 'Рассылки' },
  { href: '/moderation',    icon: Shield,           label: 'Модерация' },
  { href: '/settings',      icon: Settings,         label: 'Настройки' },
]

export default function Sidebar() {
  const path = usePathname()

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      minHeight: '100vh',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0, top: 0, bottom: 0,
      zIndex: 50,
    }}>
      {/* Logo */}
      <div style={{
        height: 'var(--header-height)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        borderBottom: '1px solid var(--border)',
        gap: 10,
      }}>
        <img src="/logo-light.svg" alt="Logo" style={{ width: 32, height: 32, objectFit: 'contain' }} />
        <span style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 800,
          fontSize: 15,
          color: 'var(--text-primary)',
          letterSpacing: '0.05em',
        }}>
          E<span style={{ color: 'var(--accent)' }}>'</span>ADMIN
        </span>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 0', overflowY: 'auto' }}>
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path.startsWith(href)
          return (
            <Link key={href} href={href} style={{ textDecoration: 'none' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 20px',
                margin: '1px 8px',
                borderRadius: 'var(--radius)',
                background: active ? 'var(--accent-dim)' : 'transparent',
                color: active ? 'var(--accent)' : 'var(--text-secondary)',
                fontWeight: active ? 600 : 400,
                fontSize: 13,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
              }}
              onMouseEnter={e => {
                if (!active) {
                  (e.currentTarget as HTMLDivElement).style.background = 'var(--bg-hover)'
                  ;(e.currentTarget as HTMLDivElement).style.color = 'var(--text-primary)'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  (e.currentTarget as HTMLDivElement).style.background = 'transparent'
                  ;(e.currentTarget as HTMLDivElement).style.color = 'var(--text-secondary)'
                }
              }}
              >
                <Icon size={15} />
                {label}
              </div>
            </Link>
          )
        })}
      </nav>

      {/* Logout */}
      <div style={{ padding: '12px 8px', borderTop: '1px solid var(--border)' }}>
        <button
          onClick={() => { removeToken(); window.location.href = '/login' }}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '9px 12px',
            borderRadius: 'var(--radius)',
            background: 'transparent',
            color: 'var(--text-muted)',
            border: 'none',
            cursor: 'pointer',
            fontSize: 13,
            fontFamily: 'var(--font-display)',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'var(--red-dim)'
            ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--red)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'transparent'
            ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'
          }}
        >
          <LogOut size={15} />
          Выйти
        </button>
      </div>
    </aside>
  )
}
