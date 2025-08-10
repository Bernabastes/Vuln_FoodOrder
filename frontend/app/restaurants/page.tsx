import Link from 'next/link'

async function fetchRestaurants() {
  const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  const res = await fetch(`${base}/api/restaurants`, { cache: 'no-store' })
  if (!res.ok) return []
  return res.json()
}

export default async function RestaurantsPage() {
  const restaurants = await fetchRestaurants()
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Our Restaurants</h1>
        <p className="text-gray-600">Discover amazing restaurants and their delicious menus</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {restaurants.map((r: any) => (
          <div key={r.id} className="rounded-lg border bg-white shadow-sm overflow-hidden">
            {r.logo_path ? (
              r.logo_path.startsWith('http') ? (
                <img src={r.logo_path} alt={`${r.name} poster`} className="h-48 w-full object-cover" />
              ) : (
                <img src={`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'}/api/uploads/${r.logo_path}`} alt={`${r.name} poster`} className="h-48 w-full object-cover" />
              )
            ) : (
              <div className="bg-gray-100 h-48 w-full" />
            )}
            <div className="p-4">
              <h2 className="text-lg font-semibold">{r.name}</h2>
              <p className="text-sm text-gray-600 mb-3">{r.address}</p>
              <Link href={`/restaurant/${r.id}`} className="inline-block bg-blue-600 text-white px-3 py-2 rounded">View Menu</Link>
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}


