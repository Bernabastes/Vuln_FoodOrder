'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'

async function fetchMenu(id: string) {
  const base =
    process.env.INTERNAL_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE ||
    'http://localhost:5001'
  const res = await fetch(`${base}/api/restaurant/${id}/menu`, {
    cache: 'no-store',
  })
  if (!res.ok) return null
  return res.json()
}

export default function RestaurantPage({
  params,
}: {
  params: { id: string }
}) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [formStates, setFormStates] = useState<any>({})

  useEffect(() => {
    fetchMenu(params.id).then((d) => {
      setData(d)
      setLoading(false)
    })
  }, [params.id])

  if (loading)
    return (
      <main className="p-6 text-center text-gray-600">Loading...</main>
    )
  if (!data)
    return (
      <main className="p-6 text-center text-gray-600">
        Restaurant not found 🍽️
      </main>
    )

  const updateFormState = (id: number, changes: any) => {
    setFormStates((prev: any) => ({
      ...prev,
      [id]: { ...prev[id], ...changes },
    }))
  }

  const handleAddToCart = async (menuItemId: number) => {
    updateFormState(menuItemId, {
      saving: true,
      message: null,
      error: null,
    })
    const base =
      process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    const { quantity = 1 } = formStates[menuItemId] || {}
    const res = await fetch(`${base}/api/cart/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        menu_item_id: menuItemId,
        quantity,
      }),
    })
    updateFormState(menuItemId, { saving: false })
    if (res.ok) {
      updateFormState(menuItemId, { message: '✅ Added to cart!' })
      setTimeout(
        () => updateFormState(menuItemId, { message: null }),
        2000
      )
    } else if (res.status === 401) {
      updateFormState(menuItemId, {
        error: '⚠️ You must be logged in to add to cart.',
      })
      setTimeout(
        () => updateFormState(menuItemId, { error: null }),
        3000
      )
    } else {
      updateFormState(menuItemId, {
        error: '❌ Failed to add. Try again!',
      })
      setTimeout(
        () => updateFormState(menuItemId, { error: null }),
        2000
      )
    }
  }

  return (
    <main className="max-w-7xl mx-auto p-6 space-y-10">
      {/* Breadcrumb */}
      <nav className="text-sm" aria-label="breadcrumb">
        <ol className="flex gap-2 text-gray-500">
          <li>
            <Link
              className="hover:text-blue-600 transition-colors"
              href="/restaurants"
            >
              Restaurants
            </Link>
          </li>
          <li>/</li>
          <li className="text-gray-800 font-medium">
            {data.restaurant.name}
          </li>
        </ol>
      </nav>

      {/* Header */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold text-gray-900">
            {data.restaurant.name}
          </h1>
          <p className="text-sm text-gray-600 mt-1 flex items-center">
            <span className="mr-1">📍</span>
            {data.restaurant.address}
          </p>
        </div>
        <Link
          href="/cart"
          className="border border-blue-600 text-blue-700 px-5 py-2 rounded-lg hover:bg-blue-600 hover:text-white transition-all"
        >
          View Cart
        </Link>
      </header>

      {/* Menu Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {data.menu_items.map((m: any) => {
          const form =
            formStates[m.id] || {
              quantity: 1,
              saving: false,
              message: null,
              error: null,
            }
          return (
            <div
              key={m.id}
              className="rounded-2xl border bg-white shadow-md overflow-hidden flex flex-col hover:shadow-xl hover:scale-[1.02] transition-all duration-300"
            >
              {m.image_path ? (
                <img
                  src={
                    m.image_path.startsWith('http')
                      ? m.image_path
                      : `${
                          process.env.NEXT_PUBLIC_API_BASE ||
                          'http://localhost:5001'
                        }/api/uploads/${m.image_path}`
                  }
                  alt={m.name}
                  className="h-56 w-full object-cover"
                />
              ) : (
                <div className="bg-gray-100 h-56 flex items-center justify-center">
                  <span className="text-gray-400">No image</span>
                </div>
              )}

              <div className="p-5 flex flex-col flex-1">
                <h2 className="font-bold text-lg text-gray-900">{m.name}</h2>
                <p className="text-sm text-gray-600 mt-1 flex-1">
                  {m.description}
                </p>
                <div className="mt-2 font-semibold text-green-700 text-lg">
                  ${Number(m.price).toFixed(2)}
                </div>

                {/* Add to Cart Form */}
                <div className="mt-4">
                  <div className="mt-2 flex flex-col gap-2 w-full">
                    <div className="flex flex-col sm:flex-row items-stretch gap-2 w-full">
                      <input
                        type="number"
                        min={1}
                        value={form.quantity}
                        onChange={(e) =>
                          updateFormState(m.id, {
                            quantity: Math.max(1, Number(e.target.value)),
                          })
                        }
                        className="w-20 border rounded-lg p-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                      />
                      <button
                        onClick={() => handleAddToCart(m.id)}
                        disabled={form.saving}
                        className={`px-5 py-2 rounded-lg font-semibold shadow transition-all duration-200 ${
                          form.saving
                            ? 'bg-green-400 cursor-not-allowed'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }`}
                      >
                        {form.saving ? 'Adding...' : 'Add'}
                      </button>
                    </div>

                    {/* Messages */}
                    {form.message && (
                      <div className="text-xs text-green-700 bg-green-100 border border-green-300 rounded-lg px-2 py-1 text-center animate-fade-in">
                        {form.message}
                      </div>
                    )}
                    {form.error && (
                      <div className="text-xs text-red-700 bg-red-100 border border-red-300 rounded-lg px-2 py-1 text-center animate-fade-in">
                        {form.error}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </section>

      {/* Go to Cart */}
      <div className="text-center">
        <Link
          href="/cart"
          className="inline-block mt-4 text-blue-600 font-medium hover:underline"
        >
          🛒 Go to cart
        </Link>
      </div>

      {/* Floating Sticky Cart Button */}
      <Link
        href="/cart"
        className="fixed bottom-6 right-6 bg-blue-600 text-white px-5 py-3 rounded-full shadow-lg hover:bg-blue-700 transition-all"
      >
        View Cart
      </Link>
    </main>
  )
}
