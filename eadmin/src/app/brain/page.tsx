'use client'
import { useEffect, useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { fetchBrainStats, fetchBrainRules, updateBrainRule, deleteBrainRule, reloadBrainRules, BrainRule, BrainStats } from '@/lib/api'
import { Brain, RefreshCw, Trash2, Plus, Save, X } from 'lucide-react'

export default function BrainPage() {
  const [stats, setStats] = useState<BrainStats | null>(null)
  const [rules, setRules] = useState<BrainRule[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<string | null>(null)
  const [editKeywords, setEditKeywords] = useState('')
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null)
  const [reloading, setReloading] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.allSettled([
      fetchBrainStats().then(setStats),
      fetchBrainRules().then(setRules),
    ]).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const showToast = (msg: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2500)
  }

  const startEdit = (rule: BrainRule) => {
    setEditing(rule.intent)
    setEditKeywords(rule.keywords.join('\n'))
  }

  const saveEdit = async (intent: string) => {
    const keywords = editKeywords.split('\n').map(k => k.trim()).filter(Boolean)
    try {
      await updateBrainRule(intent, keywords)
      setRules(prev => prev.map(r => r.intent === intent ? { ...r, keywords } : r))
      setEditing(null)
      showToast(`Правило ${intent} обновлено`)
    } catch {
      showToast('Ошибка сохранения', 'err')
    }
  }

  const deleteRule = async (intent: string) => {
    if (!confirm(`Удалить правило ${intent}?`)) return
    try {
      await deleteBrainRule(intent)
      setRules(prev => prev.filter(r => r.intent !== intent))
      showToast(`Правило ${intent} удалено`)
    } catch {
      showToast('Ошибка удаления', 'err')
    }
  }

  const reload = async () => {
    setReloading(true)
    try {
      await reloadBrainRules()
      showToast('Правила перезагружены в классификатор')
    } catch {
      showToast('Ошибка перезагрузки', 'err')
    } finally {
      setReloading(false)
    }
  }

  return (
    <AdminLayout title="Brain Editor">
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 999, padding: '10px 16px',
          borderRadius: 'var(--radius)', animation: 'fadeIn 0.2s ease',
          background: toast.type === 'ok' ? 'var(--accent-dim)' : 'var(--red-dim)',
          border: `1px solid ${toast.type === 'ok' ? 'var(--accent)' : 'var(--red)'}`,
          color: toast.type === 'ok' ? 'var(--accent)' : 'var(--red)',
          fontSize: 13, fontWeight: 600,
        }}>{toast.msg}</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Stats */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {[
              { label: 'Интентов', value: stats.total_intents },
              { label: 'Правил (дефолт)', value: stats.total_keyword_rules },
              { label: 'Кастомных правил', value: stats.custom_rules_count },
              { label: 'Кэш', value: stats.cache_active ? 'Активен' : 'Пуст' },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '16px 20px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={load} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
            background: 'var(--bg-surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', color: 'var(--text-secondary)',
            fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-display)',
          }}>
            <RefreshCw size={12} /> Обновить
          </button>
          <button onClick={reload} disabled={reloading} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
            background: 'var(--accent-dim)', border: '1px solid var(--accent)',
            borderRadius: 'var(--radius)', color: 'var(--accent)',
            fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-display)', fontWeight: 600,
            opacity: reloading ? 0.6 : 1,
          }}>
            <Brain size={12} /> {reloading ? 'Перезагрузка...' : 'Применить в Brain'}
          </button>
        </div>

        {/* Rules table */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка...</div>
        ) : rules.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: 60,
            background: 'var(--bg-surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)', color: 'var(--text-muted)',
          }}>
            <Brain size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
            <p>Кастомных правил нет. Они будут применяться поверх дефолтных.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rules.map(rule => (
              <div key={rule.intent} style={{
                background: 'var(--bg-surface)', border: `1px solid ${editing === rule.intent ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-lg)', padding: '16px 20px', transition: 'border-color 0.15s',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                  <div style={{ flex: 1 }}>
                    <code style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
                      {rule.intent}
                    </code>

                    {editing === rule.intent ? (
                      <textarea
                        value={editKeywords}
                        onChange={e => setEditKeywords(e.target.value)}
                        rows={4}
                        placeholder="Одно ключевое слово на строку..."
                        style={{
                          display: 'block', width: '100%', marginTop: 10,
                          background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                          borderRadius: 'var(--radius)', padding: '8px 12px',
                          color: 'var(--text-primary)', fontSize: 12,
                          fontFamily: 'var(--font-mono)', resize: 'vertical', outline: 'none',
                        }}
                      />
                    ) : (
                      <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {rule.keywords.map(kw => (
                          <span key={kw} style={{
                            fontSize: 11, padding: '2px 8px', borderRadius: 4,
                            background: 'var(--accent-dim)', color: 'var(--accent)',
                            fontFamily: 'var(--font-mono)',
                          }}>{kw}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {editing === rule.intent ? (
                      <>
                        <button onClick={() => saveEdit(rule.intent)} style={{
                          display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                          background: 'var(--accent)', border: 'none', borderRadius: 'var(--radius)',
                          color: 'var(--bg-base)', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                          fontFamily: 'var(--font-display)',
                        }}>
                          <Save size={11} /> Сохранить
                        </button>
                        <button onClick={() => setEditing(null)} style={{
                          padding: '6px 10px', background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                          color: 'var(--text-muted)', cursor: 'pointer',
                        }}>
                          <X size={12} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEdit(rule)} style={{
                          padding: '6px 12px', background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                          color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer',
                          fontFamily: 'var(--font-display)',
                        }}>Изменить</button>
                        <button onClick={() => deleteRule(rule.intent)} style={{
                          padding: '6px 8px', background: 'var(--red-dim)',
                          border: '1px solid var(--red)', borderRadius: 'var(--radius)',
                          color: 'var(--red)', cursor: 'pointer',
                        }}>
                          <Trash2 size={12} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  )
}
