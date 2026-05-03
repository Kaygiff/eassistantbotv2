'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { fetchUserGrowth, fetchEconomyVolume } from '@/lib/api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid } from 'recharts'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'

export default function StatsPage() {
  const [growth, setGrowth] = useState<{ date: string; count: number }[]>([])
  const [economy, setEconomy] = useState<{ date: string; credit: number; debit: number }[]>([])
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      fetchUserGrowth(days).then(data => {
        const byDate: Record<string, number> = {}
        data.forEach(d => {
          const date = d.created_at.slice(0, 10)
          byDate[date] = (byDate[date] || 0) + 1
        })
        setGrowth(Object.entries(byDate).map(([date, count]) => ({ date, count })))
      }),
      fetchEconomyVolume(days).then(data => {
        const byDate: Record<string, { credit: number; debit: number }> = {}
        data.forEach(d => {
          const date = d.created_at.slice(0, 10)
          if (!byDate[date]) byDate[date] = { credit: 0, debit: 0 }
          if (d.type === 'credit') byDate[date].credit += d.amount
          else byDate[date].debit += d.amount
        })
        setEconomy(Object.entries(byDate).map(([date, v]) => ({ date, ...v })))
      }),
    ]).finally(() => setLoading(false))
  }, [days])

  const tooltipStyle = {
    contentStyle: { background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11, fontFamily: 'var(--font-mono)' },
    labelStyle: { color: 'var(--text-primary)' },
  }

  const fmtDate = (d: string) => {
    try { return format(parseISO(d), 'd MMM', { locale: ru }) } catch { return d }
  }

  return (
    <AdminLayout title="Аналитика">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        {/* Period selector */}
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 14, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)} style={{
              padding: '7px 16px', borderRadius: 'var(--radius)',
              background: days === d ? 'var(--accent-dim)' : 'var(--bg-surface)',
              border: `1px solid ${days === d ? 'var(--accent)' : 'var(--border)'}`,
              color: days === d ? 'var(--accent)' : 'var(--text-secondary)',
              fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-display)',
            }}>{d}д</button>
          ))}
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка...</div>
        ) : (
          <>
            {/* User growth */}
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 24, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Рост пользователей
              </h2>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={growth}>
                  <defs>
                    <linearGradient id="growthGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} labelFormatter={fmtDate} formatter={(v: number) => [v, 'Новых']} />
                  <Area type="monotone" dataKey="count" stroke="var(--accent)" fill="url(#growthGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Economy */}
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 24, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Объём транзакций Ecoins
              </h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={economy}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} labelFormatter={fmtDate} />
                  <Bar dataKey="credit" name="Начислено" fill="var(--green)" radius={[3, 3, 0, 0]} maxBarSize={24} />
                  <Bar dataKey="debit" name="Списано" fill="var(--red)" radius={[3, 3, 0, 0]} maxBarSize={24} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  )
}
