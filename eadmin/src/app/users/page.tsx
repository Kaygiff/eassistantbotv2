'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { fetchUsers, banUser, unbanUser, User } from '@/lib/api'
import { Search, Ban, CheckCircle, AlertCircle } from 'lucide-react'

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterBanned, setFilterBanned] = useState<boolean | undefined>(undefined)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null)

  const load = () => {
    setLoading(true)
    fetchUsers({ search: search || undefined, is_banned: filterBanned, limit: 100 })
      .then(setUsers)
      .catch(() => showToast('Ошибка загрузки', 'err'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterBanned])

  const showToast = (msg: string, type: 'ok' | 'err') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleBan = async (user: User) => {
    setActionLoading(user.id)
    try {
      if (user.is_banned) {
        await unbanUser(user.id)
        showToast(`@${user.username || user.first_name} разблокирован`, 'ok')
      } else {
        await banUser(user.id, 'Admin action')
        showToast(`@${user.username || user.first_name} заблокирован`, 'ok')
      }
      load()
    } catch {
      showToast('Ошибка', 'err')
    } finally {
      setActionLoading(null)
    }
  }

  const filtered = users.filter(u =>
    !search || u.username?.includes(search) || u.first_name?.includes(search) ||
    String(u.telegram_id).includes(search)
  )

  const LANG_FLAGS: Record<string, string> = { ru: '🇷🇺', en: '🇬🇧', kz: '🇰🇿', uz: '🇺🇿', by: '🇧🇾', tj: '🇹🇯', tm: '🇹🇲', kg: '🇰🇬' }

  return (
    <AdminLayout title="Пользователи">
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 999,
          padding: '10px 16px', borderRadius: 'var(--radius)',
          background: toast.type === 'ok' ? 'var(--green-dim)' : 'var(--red-dim)',
          border: `1px solid ${toast.type === 'ok' ? 'var(--green)' : 'var(--red)'}`,
          color: toast.type === 'ok' ? 'var(--green)' : 'var(--red)',
          fontSize: 13, fontWeight: 600, animation: 'fadeIn 0.2s ease',
        }}>
          {toast.msg}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Filters */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
            <Search size={13} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              placeholder="Поиск по username, имени, ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
              style={{
                width: '100%', paddingLeft: 34, paddingRight: 14, paddingTop: 9, paddingBottom: 9,
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', color: 'var(--text-primary)',
                fontSize: 13, fontFamily: 'var(--font-display)', outline: 'none',
              }}
            />
          </div>

          {[
            { label: 'Все', value: undefined },
            { label: 'Активные', value: false },
            { label: 'Забаненные', value: true },
          ].map(({ label, value }) => (
            <button key={label} onClick={() => setFilterBanned(value)}
              style={{
                padding: '8px 16px', borderRadius: 'var(--radius)',
                background: filterBanned === value ? 'var(--accent-dim)' : 'var(--bg-surface)',
                border: `1px solid ${filterBanned === value ? 'var(--accent)' : 'var(--border)'}`,
                color: filterBanned === value ? 'var(--accent)' : 'var(--text-secondary)',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-display)',
              }}
            >{label}</button>
          ))}

          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {filtered.length} записей
          </span>
        </div>

        {/* Table */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка...</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Пользователь', 'Telegram ID', 'Язык', 'Ассистент', 'Дата', 'Статус', ''].map(h => (
                    <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((user, i) => (
                  <tr key={user.id} style={{ borderBottom: i < filtered.length - 1 ? '1px solid var(--border)' : 'none', transition: 'background 0.1s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                        {user.first_name || '—'}
                      </div>
                      {user.username && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>@{user.username}</div>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>{user.telegram_id}</td>
                    <td style={{ padding: '12px 16px', fontSize: 16 }}>{LANG_FLAGS[user.language] || user.language.toUpperCase()}</td>
                    <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-secondary)' }}>{user.assistant_name}</td>
                    <td style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {new Date(user.created_at).toLocaleDateString('ru')}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
                        background: user.is_banned ? 'var(--red-dim)' : 'var(--green-dim)',
                        color: user.is_banned ? 'var(--red)' : 'var(--green)',
                        letterSpacing: '0.06em',
                      }}>
                        {user.is_banned ? 'BANNED' : 'ACTIVE'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <button
                        disabled={actionLoading === user.id}
                        onClick={() => handleBan(user)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 5,
                          padding: '5px 10px', borderRadius: 'var(--radius)',
                          background: user.is_banned ? 'var(--green-dim)' : 'var(--red-dim)',
                          border: `1px solid ${user.is_banned ? 'var(--green)' : 'var(--red)'}`,
                          color: user.is_banned ? 'var(--green)' : 'var(--red)',
                          fontSize: 11, fontWeight: 600, cursor: 'pointer',
                          fontFamily: 'var(--font-display)',
                          opacity: actionLoading === user.id ? 0.5 : 1,
                        }}
                      >
                        {user.is_banned
                          ? <><CheckCircle size={11} /> Разбан</>
                          : <><Ban size={11} /> Бан</>
                        }
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
