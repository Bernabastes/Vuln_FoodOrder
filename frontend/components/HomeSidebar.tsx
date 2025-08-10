'use client'
import { useEffect, useState } from 'react'

export default function HomeSidebar() {
  const [me, setMe] = useState<{ user: { username: string } | null }>({ user: null })
  const [q, setQ] = useState('')

  useEffect(() => {
    (async () => {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      const res = await fetch(`${base}/api/me`, { credentials: 'include' })
      if (res.ok) setMe(await res.json())
    })()
  }, [])

  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-white shadow">
        <div className="border-b px-4 py-3">
          <h5 className="font-semibold">Search Menu Items</h5>
        </div>
        <div className="p-4">
          <form action="/search">
            <div className="flex gap-2">
              <input name="q" value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Search for dishes..." className="flex-1 border rounded p-2" />
              <button className="px-3 py-2 bg-blue-600 text-white rounded">Search</button>
            </div>
          </form>
        </div>
      </div>

      {me.user ? (
        <div className="rounded-lg border bg-white shadow">
          <div className="border-b px-4 py-3">
            <h5 className="font-semibold">Quick Actions</h5>
          </div>
          <div className="p-4 space-y-2">
            <a href="/dashboard" className="inline-block w-full text-center border border-blue-600 text-blue-700 px-3 py-2 rounded">View Dashboard</a>
            <a href="/cart" className="inline-block w-full text-center border border-green-600 text-green-700 px-3 py-2 rounded">View Cart</a>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border bg-white shadow">
          <div className="border-b px-4 py-3">
            <h5 className="font-semibold">Get Started</h5>
          </div>
          <div className="p-4 space-y-2">
            <a href="/login" className="inline-block w-full text-center bg-blue-600 text-white px-3 py-2 rounded">Login</a>
            <a href="/register" className="inline-block w-full text-center border border-blue-600 text-blue-700 px-3 py-2 rounded">Register</a>
          </div>
        </div>
      )}
    </div>
  )
}


