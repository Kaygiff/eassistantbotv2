import type { Metadata } from 'next'
import './globals.css'
import { ToastProvider } from '@/components/Toast'

export const metadata: Metadata = {
  title: "EAdmin — E'assistant",
  description: "Admin panel for E'assistant AI Telegram Bot Platform",
  manifest: '/manifest.json',
  icons: {
    icon: '/logo-dark.png',
    apple: '/logo-dark.png',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  )
}
