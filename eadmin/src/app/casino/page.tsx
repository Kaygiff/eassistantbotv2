'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { fetchCasinoStats } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { TrendingUp, TrendingDown, Coins, Trophy } from 'lucide-react'

interface CasinoStats {
  total_rounds: number
  total_bet: number
  total_payout: number
  total_house_fee: number
  wins: number
  losses: number
  by_game: Record<string, { rounds: number; bet: number; payout: number; house: number }>
}

const GAME_ICONS: Record<string, string> = {
  slots: '🎰', roulette: '🎡', blackjack: '🃏',
  crash: '📈', poker: '♠️',
}

export default function CasinoPage() {
  const [stats, setStats] = useState<CasinoStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCasinoStats()
      .then(data => setStats(data as CasinoStats))
      .finally(() => setLoading(false))
  }, [])

  const byGameData = stats
    ? Object.entries(stats.by_game).map(([name, data]) => ({
        name: `${GAME_ICONS[name] || '🎮'} ${name}`,
        rounds: (data as { rounds: number }).rounds,
        house: (data as { house: number }).house,
      }))
    : []

  const winRate = stats ? Math.round((stats.wins / Math.max(stats.total_rounds, 1)) * 100) : 0

  const tooltipStyle = {
    contentStyle: { background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11, fontFamily: 'var(--font-mono)' },
    labelStyle: { color: 'var(--text-primary)' },
  }

  return (
    <AdminLayout title="Казино">
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)' }}>
          Загрузка...
        </div>
      ) : !stats ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Нет данных</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* Main stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
            {[
              { label: 'Всего раундов', value: stats.total_rounds.toLocaleString(), icon: '🎮', color: 'var(--accent)' },
              { label: 'Ставок (EC)', value: stats.total_bet.toLocaleString(), icon: '💰', color: 'var(--yellow)' },
              { label: 'Доход казино', value: stats.total_house_fee.toLocaleString(), icon: '🏦', color: 'var(--green)' },
              { label: 'Побед игроков', value: `${winRate}%`, icon: '🏆', color: 'var(--accent-bright)' },
            ].map(({ label, value, icon, color }) => (
              <div key={label} style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)', padding: '20px 22px',
              }}>
                <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>{label}</div>
                <div style={{ fontSize: 24, fontWeight: 800, fontFamily: 'var(--font-mono)', color }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Win/Loss ratio */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 20, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Побед vs Поражений
            </h2>
            <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
              <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--bg-elevated)', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${winRate}%`,
                  background: `linear-gradient(90deg, var(--green), var(--accent))`,
                  borderRadius: 4, transition: 'width 0.5s ease',
                }} />
              </div>
              <div style={{ display: 'flex', gap: 20, flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <TrendingUp size={13} color="var(--green)" />
                  <span style={{ fontSize: 12, color: 'var(--green)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {stats.wins.toLocaleString()} побед
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <TrendingDown size={13} color="var(--red)" />
                  <span style={{ fontSize: 12, color: 'var(--red)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {stats.losses.toLocaleString()} поражений
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* By game */}
          {byGameData.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 24, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                По играм
              </h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={byGameData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={100} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="rounds" name="Раундов" fill="var(--accent)" radius={[0, 4, 4, 0]} maxBarSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Revenue by game table */}
          {Object.keys(stats.by_game).length > 0 && (
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Игра', 'Раундов', 'Ставок (EC)', 'Доход казино'].map(h => (
                      <th key={h} style={{ padding: '12px 20px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.by_game).map(([game, data], i, arr) => {
                    const d = data as { rounds: number; bet: number; house: number }
                    return (
                      <tr key={game} style={{ borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      >
                        <td style={{ padding: '12px 20px', fontSize: 14 }}>{GAME_ICONS[game] || '🎮'} <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{game}</span></td>
                        <td style={{ padding: '12px 20px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)' }}>{d.rounds.toLocaleString()}</td>
                        <td style={{ padding: '12px 20px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--yellow)' }}>{d.bet.toLocaleString()}</td>
                        <td style={{ padding: '12px 20px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--green)' }}>{d.house.toLocaleString()}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </AdminLayout>
  )
}
