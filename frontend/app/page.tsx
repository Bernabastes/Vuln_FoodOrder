async function fetchRestaurants() {
  const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  const res = await fetch(`${base}/api/restaurants`, { cache: 'no-store' })
  if (!res.ok) return []
  return res.json()
}

import Link from 'next/link'
import HomeSidebar from '../components/HomeSidebar'

export default async function HomePage() {
  const restaurants = await fetchRestaurants()
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-8">
      <section className="grid md:grid-cols-3 gap-6 items-stretch">
        <div className="md:col-span-2 rounded-2xl shadow relative overflow-hidden p-8" style={{background:"linear-gradient(135deg,#ef4444,#f97316)"}}>
          <h1 className="text-4xl font-extrabold text-white mb-3">Welcome to VulnEats</h1>
          <p className="text-orange-50 text-lg">Order delicious food from your favorite restaurants with just a few clicks!</p>
          <hr className="my-6 opacity-50" />
          <p className="text-orange-50 mb-6">Discover amazing dishes, place orders, and track your delivery in real-time.</p>
          <Link href="/restaurants" className="inline-flex items-center gap-2 bg-white/90 text-red-700 hover:bg-white px-4 py-2 rounded">
            <span>🍽️</span>
            <span>Browse Restaurants</span>
          </Link>
        </div>
        <HomeSidebar />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Featured Restaurants</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {restaurants.slice(0, 2).map((r: any) => (
            <div key={r.id} className="rounded-2xl overflow-hidden bg-white shadow-sm border">
              <div className="relative h-56 bg-gray-100">
                {/* Static promos for look-and-feel */}
                <img src={r.id === 1 ? 'https://images.unsplash.com/photo-1542281286-9e0a16bb7366?q=80&w=1200&auto=format&fit=crop' : 'https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1200&auto=format&fit=crop'} alt="cover" className="h-full w-full object-cover" />
                <span className={`absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-semibold ${r.id === 1 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{r.id === 1 ? 'Italian' : 'American'}</span>
              </div>
              <div className="p-5">
                <h3 className="text-xl font-semibold mb-1">{r.name}</h3>
                <div className="flex items-center gap-2 text-amber-500 text-sm mb-1">{'★★★★★'}<span className="text-gray-500">4.7</span><span className="text-gray-400">(100+ reviews)</span></div>
                <p className="text-gray-700 mb-4">Delicious meals with fresh ingredients and authentic recipes.</p>
                <Link href={`/restaurant/${r.id}`} className={`inline-block w-full text-center px-4 py-2 rounded ${r.id === 1 ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'}`}>View Menu</Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="rounded-2xl overflow-hidden shadow">
          <div className="relative">
            <img src="https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?q=80&w=1600&auto=format&fit=crop" alt="promo" className="w-full h-40 md:h-56 object-cover" />
            <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center text-white text-center px-4">
              <h3 className="text-xl md:text-2xl font-semibold mb-1">🎉 Special Offer!</h3>
              <p className="text-sm md:text-base">Get 20% off your first order with code WELCOME20</p>
              <Link href="/restaurants" className="mt-3 inline-block bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded">Order Now</Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}


