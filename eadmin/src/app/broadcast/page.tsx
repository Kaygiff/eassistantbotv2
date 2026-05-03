'use client'
import { useState } from 'react'
import AdminLayout from '@/components/AdminLayout'
import { sendBroadcast } from '@/lib/api'
import { Send, AlertTriangle } from 'lucide-react'

const LANGS = [
  { code: undefined, label: '🌐 Всем' },
  { code: 'ru', label: '🇷🇺 Русский' },
  { code: 'en', label: '🇬🇧 English' },
  { code: 'kz', label: '🇰🇿 Казахский' },
  { code: 'uz', label: '🇺🇿 Узбекский' },
]

export default function BroadcastPage() {
  const [text, setText] = useState('')
  const [lang, setLang] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSend = async () => {
    if (!text.trim()) return
    if (!confirm(`Отправить рассылку ${lang ? `для языка ${lang}` : 'ВСЕМ пользователям'}?`)) return

    setLoading(true)
    setError('')
    try {
      await sendBroadcast(text, lang)
      setSent(true)
      setText('')
      setTimeout(() => setSent(false), 4000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка отправки')
    } finally {
      setLoading(false)
    }
  }

  const charCount = text.length

  return (
    <AdminLayout title="Рассылки">
      <div style={{ maxWidth: 680, display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Warning */}
        <div style={{
          display: 'flex', gap: 12, alignItems: 'flex-start',
          padding: '14px 18px', borderRadius: 'var(--radius-lg)',
          background: 'var(--yellow-dim)', border: '1px solid var(--yellow)',
        }}>
          <AlertTriangle size={16} style={{ color: 'var(--yellow)', flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: 13, color: 'var(--yellow)', lineHeight: 1.5 }}>
            Рассылка отправляется через Celery-очередь асинхронно. Массовые рассылки обрабатываются в фоне и могут занять несколько минут.
          </p>
        </div>

        {/* Language selector */}
        <div>
          <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 10 }}>
            Целевая аудитория
          </label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {LANGS.map(({ code, label }) => (
              <button key={String(code)} onClick={() => setLang(code)} style={{
                padding: '8px 16px', borderRadius: 'var(--radius)',
                background: lang === code ? 'var(--accent-dim)' : 'var(--bg-surface)',
                border: `1px solid ${lang === code ? 'var(--accent)' : 'var(--border)'}`,
                color: lang === code ? 'var(--accent)' : 'var(--text-secondary)',
                fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-display)', fontWeight: lang === code ? 600 : 400,
              }}>{label}</button>
            ))}
          </div>
        </div>

        {/* Text editor */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Текст сообщения (Markdown)
            </label>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: charCount > 4000 ? 'var(--red)' : 'var(--text-muted)' }}>
              {charCount} / 4096
            </span>
          </div>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="*Жирный*, _курсив_, `код`&#10;&#10;Напиши текст рассылки здесь..."
            rows={10}
            style={{
              width: '100%',
              background: 'var(--bg-surface)', border: `1px solid ${error ? 'var(--red)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-lg)', padding: '14px 16px',
              color: 'var(--text-primary)', fontSize: 14, fontFamily: 'var(--font-display)',
              resize: 'vertical', outline: 'none', lineHeight: 1.6, transition: 'border-color 0.15s',
            }}
            onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
            onBlur={e => (e.target.style.borderColor = error ? 'var(--red)' : 'var(--border)')}
          />
        </div>

        {/* Preview */}
        {text && (
          <div style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)', padding: '16px 20px',
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
              Превью (упрощённое)
            </div>
            <div style={{ fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {text}
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '10px 14px', borderRadius: 'var(--radius)', background: 'var(--red-dim)', border: '1px solid var(--red)', color: 'var(--red)', fontSize: 13 }}>
            {error}
          </div>
        )}

        {sent && (
          <div style={{ padding: '10px 14px', borderRadius: 'var(--radius)', background: 'var(--green-dim)', border: '1px solid var(--green)', color: 'var(--green)', fontSize: 13, fontWeight: 600 }}>
            ✅ Рассылка поставлена в очередь!
          </div>
        )}

        <button
          onClick={handleSend}
          disabled={loading || !text.trim() || charCount > 4096}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            padding: '14px', width: '100%',
            background: loading || !text.trim() ? 'var(--bg-elevated)' : 'var(--accent)',
            color: loading || !text.trim() ? 'var(--text-muted)' : 'var(--bg-base)',
            border: 'none', borderRadius: 'var(--radius-lg)',
            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14,
            cursor: loading || !text.trim() ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s', letterSpacing: '0.05em',
          }}
        >
          <Send size={15} />
          {loading ? 'Отправка...' : `Отправить ${lang ? `(${lang.toUpperCase()})` : '(всем)'}`}
        </button>
      </div>
    </AdminLayout>
  )
}
