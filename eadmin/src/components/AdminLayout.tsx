'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/api'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AdminLayout({ children, title }: { children: React.ReactNode; title: string }) {
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated()) router.push('/login')
  }, [router])

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Sidebar />
      <div style={{ flex: 1, marginLeft: 'var(--sidebar-width)', display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header title={title} />
        <main style={{ flex: 1, padding: '28px', animation: 'fadeIn 0.25s ease' }}>
          {children}
        </main>
      </div>
    </div>
  )
}
