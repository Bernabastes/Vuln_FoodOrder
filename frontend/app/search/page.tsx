import Link from 'next/link'

async function searchItems(q: string) {
  const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  const res = await fetch(`${base}/api/search?q=${encodeURIComponent(q)}`, { cache: 'no-store' })
  if (!res.ok) return []
  return res.json()
}

export default async function SearchPage({ searchParams }: { searchParams: { q?: string } }) {
  const q = searchParams.q || ''
  const items = q ? await searchItems(q) : []
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <form className="flex gap-3">
          <input name="q" defaultValue={q} className="flex-1 border rounded p-2" placeholder="Search dishes..." />
          <button className="px-4 py-2 bg-blue-600 text-white rounded">Search</button>
        </form>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {items.map((m: any) => (
          <Link key={m.id} href={`/restaurant/${m.restaurant_id}`} className="rounded-lg border p-5 bg-white shadow-sm block hover:shadow">
            <div className="font-semibold text-lg">{m.name}</div>
            <div className="text-sm text-gray-700 line-clamp-2">{m.description}</div>
            <div className="mt-2 font-medium">{`$${m.price}`}</div>
          </Link>
        ))}
      </div>
    </main>
  )
}


