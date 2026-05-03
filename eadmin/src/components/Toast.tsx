'use client'
import { useEffect, useState, createContext, useContext, useCallback } from 'react'
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'

type ToastType = 'ok' | 'err' | 'warn'

interface ToastItem {
  id: string
  msg: string
  type: ToastType
}

interface ToastContextValue {
  toast: (msg: string, type?: ToastType) => void
  ok: (msg: string) => void
  err: (msg: string) => void
  warn: (msg: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((msg: string, type: ToastType = 'ok') => {
    const id = Math.random().toString(36).slice(2)
    setToasts(prev => [...prev, { id, msg, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500)
  }, [])

  const ctx: ToastContextValue = {
    toast: addToast,
    ok: (msg) => addToast(msg, 'ok'),
    err: (msg) => addToast(msg, 'err'),
    warn: (msg) => addToast(msg, 'warn'),
  }

  return (
    <ToastContext.Provider value={ctx}>
      {children}
      {/* Toast container */}
      <div style={{
        position: 'fixed', top: 20, right: 20, zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: 8,
        pointerEvents: 'none',
      }}>
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onClose={() => setToasts(prev => prev.filter(x => x.id !== t.id))} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onClose }: { toast: ToastItem; onClose: () => void }) {
  const COLORS = {
    ok:   { bg: 'var(--green-dim)',   border: 'var(--green)',   color: 'var(--green)' },
    err:  { bg: 'var(--red-dim)',     border: 'var(--red)',     color: 'var(--red)' },
    warn: { bg: 'var(--yellow-dim)',  border: 'var(--yellow)',  color: 'var(--yellow)' },
  }

  const ICONS = {
    ok:   <CheckCircle size={14} />,
    err:  <XCircle size={14} />,
    warn: <AlertCircle size={14} />,
  }

  const { bg, border, color } = COLORS[toast.type]

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 14px',
      background: bg, border: `1px solid ${border}`,
      borderRadius: 'var(--radius)', color,
      fontSize: 13, fontWeight: 600,
      animation: 'fadeIn 0.2s ease',
      pointerEvents: 'all',
      minWidth: 240, maxWidth: 360,
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    }}>
      {ICONS[toast.type]}
      <span style={{ flex: 1 }}>{toast.msg}</span>
      <button
        onClick={onClose}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color, opacity: 0.7, padding: 0, display: 'flex' }}
      >
        <X size={12} />
      </button>
    </div>
  )
}
