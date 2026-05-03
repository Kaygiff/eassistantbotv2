import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  color?: string
  trend?: { value: number; label: string }
  mono?: boolean
}

export default function StatCard({ label, value, icon: Icon, color = 'var(--accent)', trend, mono }: StatCardProps) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      transition: 'border-color 0.2s',
      cursor: 'default',
    }}
    onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
    onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          {label}
        </span>
        <div style={{
          width: 32, height: 32,
          borderRadius: 8,
          background: `${color}18`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={15} color={color} />
        </div>
      </div>
      <div style={{
        fontSize: 28,
        fontWeight: 800,
        color: 'var(--text-primary)',
        letterSpacing: '-0.03em',
        fontFamily: mono ? 'var(--font-mono)' : 'var(--font-display)',
        lineHeight: 1,
      }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {trend && (
        <div style={{ fontSize: 11, color: trend.value >= 0 ? 'var(--green)' : 'var(--red)' }}>
          {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
        </div>
      )}
    </div>
  )
}
