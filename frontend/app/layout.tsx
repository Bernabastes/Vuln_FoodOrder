export const metadata = {
  title: 'VulnEats',
  description: 'Food ordering demo (Next.js frontend)'
}

import './globals.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import { cookies } from 'next/headers'

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  const cookieHeader = cookies().toString()
  let initialMe: any = { user: null }
  try {
    const res = await fetch(`${base}/api/me`, { headers: { Cookie: cookieHeader }, cache: 'no-store' })
    if (res.ok) initialMe = await res.json()
  } catch {}
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 flex flex-col">
        <NavBar initialMe={initialMe} />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  )
}


