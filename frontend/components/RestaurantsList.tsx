"use client"

import Link from 'next/link'
import { useEffect, useState } from 'react'

export default function RestaurantsList() {
  const [restaurants, setRestaurants] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      const res = await fetch(`${base}/api/restaurants`, { cache: 'no-store' })
      if (!res.ok) {
        setRestaurants([])
      } else {
        setRestaurants(await res.json())
      }
      setLoading(false)
    }
    fetchData()
  }, [])
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1,2,3].map(i => (
          <div key={i} className="rounded-lg border bg-white shadow-sm overflow-hidden animate-pulse">
            <div className="bg-gray-200 h-48 w-full" />
            <div className="p-4">
              <div className="h-6 bg-gray-200 rounded w-2/3 mb-2" />
              <div className="h-4 bg-gray-100 rounded w-1/2 mb-3" />
              <div className="h-8 bg-blue-100 rounded w-full" />
            </div>
          </div>
        ))}
      </div>
    )
  }
  return (
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
  )
}
