'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'

type Me = { user: { id: number; username: string; role: string } | null }

export default function NavBar() {
  const [me, setMe] = useState<Me>({ user: null })

  useEffect(() => {
    ;(async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
        const res = await fetch(`${base}/api/me`, { credentials: 'include' })
        if (res.ok) setMe(await res.json())
      } catch {}
    })()
  }, [])

  return (
    <nav className="bg-white border-b shadow-sm">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-semibold text-lg">VulnEats</Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/restaurants" className="text-gray-700 hover:text-black">Restaurants</Link>
          <Link href="/search" className="text-gray-700 hover:text-black">Search</Link>
          <Link href="/cart" className="text-gray-700 hover:text-black">Cart</Link>
          {me.user ? (
            <>
              <Link href="/dashboard" className="text-gray-700 hover:text-black">Dashboard</Link>
              <button
                className="text-red-600 hover:text-red-700"
                onClick={async () => {
                  const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
                  await fetch(`${base}/api/logout`, { method: 'POST', credentials: 'include' })
                  location.href = '/'
                }}
              >Logout</button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-gray-700 hover:text-black">Login</Link>
              <Link href="/register" className="text-gray-700 hover:text-black">Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}


