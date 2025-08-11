'use client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    const res = await fetch(`${base}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, email, password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(()=>({}))
      setError(data?.message || 'Registration failed')
      return
    }
    router.push('/login')
  }

  return (
    <main className="max-w-md mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Create account</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Username</label>
            <input className="w-full border rounded p-2" placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input className="w-full border rounded p-2" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input className="w-full border rounded p-2" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button className="w-full bg-blue-600 text-white px-4 py-2 rounded" type="submit">Sign up</button>
        </form>
        <div className="mt-4 text-sm text-center">
          <span>Already have an account? </span>
          <Link href="/login" className="text-blue-600 hover:underline">Log in</Link>
        </div>
      </div>
    </main>
  )
}


