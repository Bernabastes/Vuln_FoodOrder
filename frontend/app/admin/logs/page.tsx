'use client'
import { useEffect, useState } from 'react'

export default function LogsPage() {
  const [lines, setLines] = useState<string[]>([])
  useEffect(() => {
    (async ()=>{
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      // Forward ?admin=1 from the page URL to intentionally trigger the bypass
      const params = new URLSearchParams(window.location.search)
      const adminFlag = params.get('admin') || '0'
      const res = await fetch(`${base}/api/admin/logs?admin=${encodeURIComponent(adminFlag)}`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setLines(data.lines || [])
      }
    })()
  }, [])
  return (
    <main className="max-w-5xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Logs</h1>
        <pre className="bg-black text-green-300 p-4 rounded overflow-auto text-sm whitespace-pre-wrap h-96">{lines.join('')}</pre>
      </div>
    </main>
  )
}


