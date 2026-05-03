'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import StatCard from '@/components/StatCard'
import { fetchDashboard, fetchCasinoStats, fetchLanguageStats } from '@/lib/api'
import { Users, Ban, MessageSquare, Coins, Globe, TrendingUp } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const LANG_COLORS: Record<string, string> = {
  ru: '#4ecdc4', en: '#7fffd4', kz: '#3db8b0',
  uz: '#2a9e96', by: '#1d8880', tj: '#156b65',
  tm: '#0e504c', kg: '#083634',
}

export default function DashboardPage() {
  const [dash, setDash] = useState<{ users_total: number; users_banned: number; groups_total: number; transactions_total: number } | null>(null)
  const [casino, setCasino] = useState<{ total_rounds: number; total_bet: number; total_house_fee: number; wins: number; losses: number } | null>(null)
  const [langs, setLangs] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      fetchDashboard().then(setDash),
      fetchCasinoStats().then(setCasino),
      fetchLanguageStats().then(setLangs),
    ]).finally(() => setLoading(false))
  }, [])

  const langData = Object.entries(langs).map(([name, value]) => ({ name: name.toUpperCase(), value }))

  return (
    <AdminLayout title="Дашборд">
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)' }}>
          Загрузка...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

          {/* Main stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <StatCard label="Пользователей" value={dash?.users_total ?? 0} icon={Users} color="var(--accent)" />
            <StatCard label="Заблокировано" value={dash?.users_banned ?? 0} icon={Ban} color="var(--red)" />
            <StatCard label="Групп" value={dash?.groups_total ?? 0} icon={MessageSquare} color="var(--yellow)" />
            <StatCard label="Транзакций" value={dash?.transactions_total ?? 0} icon={Coins} color="var(--green)" mono />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Casino stats */}
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: 24,
            }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 20, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Казино
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                {[
                  { label: 'Раундов', value: casino?.total_rounds ?? 0 },
                  { label: 'Ставок (EC)', value: casino?.total_bet?.toLocaleString() ?? 0 },
                  { label: 'Доход казино', value: casino?.total_house_fee?.toLocaleString() ?? 0 },
                  { label: 'Побед игроков', value: casino?.wins ?? 0 },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Language distribution */}
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: 24,
            }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 20, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Языки
              </h2>
              {langData.length > 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <ResponsiveContainer width={120} height={120}>
                    <PieChart>
                      <Pie data={langData} cx="50%" cy="50%" innerRadius={30} outerRadius={55} dataKey="value" strokeWidth={0}>
                        {langData.map(entry => (
                          <Cell key={entry.name} fill={LANG_COLORS[entry.name.toLowerCase()] || 'var(--accent)'} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                        labelStyle={{ color: 'var(--text-primary)' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {langData.slice(0, 6).map(({ name, value }) => (
                      <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 8, height: 8, borderRadius: 2, background: LANG_COLORS[name.toLowerCase()] || 'var(--accent)', flexShrink: 0 }} />
                        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{name}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Нет данных</div>
              )}
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  )
}
