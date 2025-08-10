'use client'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    const res = await fetch(`${base}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      setError('Invalid credentials')
      return
    }
    // Hard refresh so server components/layout re-fetch with new auth cookie
    window.location.href = '/dashboard'
  }

  return (
    <main className="max-w-md mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Login</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Username</label>
            <input className="w-full border rounded p-2" placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input className="w-full border rounded p-2" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button className="w-full bg-blue-600 text-white px-4 py-2 rounded" type="submit">Sign in</button>
        </form>
      </div>
    </main>
  )
}


