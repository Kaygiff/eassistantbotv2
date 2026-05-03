import React from 'react'

export interface Column<T> {
  key: string
  header: string
  width?: number | string
  render?: (row: T) => React.ReactNode
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyText?: string
  emptyIcon?: React.ReactNode
  rowKey: (row: T) => string
}

export default function Table<T>({
  columns,
  data,
  loading = false,
  emptyText = 'Нет данных',
  emptyIcon,
  rowKey,
}: TableProps<T>) {
  if (loading) {
    return (
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: 40,
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: 13,
      }}>
        <div style={{
          width: 20, height: 20, borderRadius: '50%',
          border: '2px solid var(--border)',
          borderTopColor: 'var(--accent)',
          animation: 'spin 0.8s linear infinite',
          margin: '0 auto 12px',
        }} />
        Загрузка...
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '48px 24px',
        textAlign: 'center',
        color: 'var(--text-muted)',
      }}>
        {emptyIcon && <div style={{ marginBottom: 12, opacity: 0.4 }}>{emptyIcon}</div>}
        <p style={{ fontSize: 13 }}>{emptyText}</p>
      </div>
    )
  }

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
    }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            {columns.map(col => (
              <th
                key={col.key}
                style={{
                  padding: '11px 16px',
                  textAlign: 'left',
                  fontSize: 10,
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  whiteSpace: 'nowrap',
                  width: col.width,
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={rowKey(row)}
              style={{
                borderBottom: i < data.length - 1 ? '1px solid var(--border)' : 'none',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              {columns.map(col => (
                <td key={col.key} style={{ padding: '11px 16px' }}>
                  {col.render
                    ? col.render(row)
                    : <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{String((row as Record<string, unknown>)[col.key] ?? '—')}</span>
                  }
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
