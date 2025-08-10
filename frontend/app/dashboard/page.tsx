'use client'
import { useEffect, useMemo, useState, useRef } from 'react'

type DashboardData = {
  role: 'customer' | 'owner' | 'admin'
  orders?: any[]
  restaurants?: any[]
  restaurant?: any
  menu_items?: any[]
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUnauthorized, setIsUnauthorized] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [createMessage, setCreateMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [deletingRestaurant, setDeletingRestaurant] = useState<number | null>(null)
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    const load = async () => {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      try {
        const res = await fetch(`${base}/api/dashboard`, { credentials: 'include' })
        if (res.status === 401) {
          setIsUnauthorized(true)
          return
        }
        if (res.ok) {
          const dashboardData = await res.json()
          setData(dashboardData)
        }
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  if (isLoading) {
    return (
      <main className="max-w-4xl mx-auto p-6">
        <div className="bg-white border rounded-lg shadow p-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-40 mb-4" />
          <div className="h-4 bg-gray-200 rounded w-24" />
        </div>
      </main>
    )
  }

  if (isUnauthorized || !data) {
    return (
      <main className="max-w-4xl mx-auto p-6">
        <div className="bg-white border rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold mb-2">Dashboard</h1>
          <p>Please <a className="text-blue-600 underline" href="/login">login</a>.</p>
        </div>
      </main>
    )
  }

  const statusBadge = (s: string) => {
    const map: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      cooking: 'bg-cyan-100 text-cyan-800',
      delivered: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800'
    }
    return <span className={`px-3 py-1 rounded-full text-xs font-semibold ${map[s] || 'bg-gray-100 text-gray-800'}`}>{s}</span>
  }

  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Dashboard ({data.role})</h1>

      {data.role === 'customer' && (
        <div className="grid md:grid-cols-3 gap-6">
          <section className="md:col-span-2 bg-white border rounded-lg shadow p-6">
            <div className="border-b pb-3 mb-4"><h2 className="font-semibold">Order History</h2></div>
            {data.orders && data.orders.length > 0 ? (
              <div className="space-y-4">
                {data.orders.map((o: any) => (
                  <div key={o.id} className="grid grid-cols-3 gap-4 items-center border-b pb-3">
                    <div className="col-span-2">
                      <h6 className="font-semibold">Order #{o.id}</h6>
                      <p className="text-sm text-gray-600">
                        🍽️ {o.restaurant_name}
                        <br />
                        📅 {o.created_at}
                        <br />
                        <span className="font-semibold">Total:</span> ${o.total_amount}
                      </p>
                    </div>
                    <div className="text-right">{statusBadge(o.status)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-600">No orders yet. <a className="text-blue-600 underline" href="/restaurants">Browse restaurants</a></div>
            )}
          </section>
          <aside className="space-y-4">
            <div className="bg-white border rounded-lg shadow">
              <div className="border-b px-4 py-3"><h5 className="font-semibold">Quick Actions</h5></div>
              <div className="p-4 space-y-2">
                <a href="/restaurants" className="btn border border-blue-600 text-blue-700 block text-center px-3 py-2 rounded">Browse Restaurants</a>
                <a href="/cart" className="btn border border-gray-400 text-gray-700 block text-center px-3 py-2 rounded">View Cart</a>
                <a href="/search" className="btn border border-gray-400 text-gray-700 block text-center px-3 py-2 rounded">Search Menu Items</a>
              </div>
            </div>
            <div className="bg-white border rounded-lg shadow">
              <div className="border-b px-4 py-3"><h5 className="font-semibold">Popular Restaurants</h5></div>
              <div className="p-4 space-y-2">
                {data.restaurants?.map((r: any) => (
                  <div key={r.id}>
                    <a href={`/restaurant/${r.id}`} className="text-blue-700 hover:underline">🍽️ {r.name}</a>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}

      {data.role === 'owner' && (
        <div className="grid md:grid-cols-3 gap-6">
          <section className="md:col-span-2 bg-white border rounded-lg shadow">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h5 className="font-semibold">Recent Orders</h5>
              <span className="inline-flex items-center justify-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">{data.orders?.length || 0} orders</span>
            </div>
            <div className="p-6">
              {data.orders && data.orders.length > 0 ? (
                <div className="space-y-4">
                  {data.orders.map((o: any) => (
                    <div key={o.id} className="grid md:grid-cols-2 gap-4 border-b pb-3">
                      <div>
                        <h6 className="font-semibold">Order #{o.id}</h6>
                        <p className="text-sm text-gray-600">👤 {o.username}<br />📅 {o.created_at}<br /><span className="font-semibold">Total:</span> ${o.total_amount}</p>
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        <select defaultValue={o.status} className="border rounded p-2 text-sm">
                          {['pending','cooking','delivered','cancelled'].map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <button className="px-3 py-2 text-sm bg-blue-600 text-white rounded" onClick={async (e)=>{
                          const status = (e.currentTarget.previousSibling as HTMLSelectElement).value
                          const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
                          await fetch(`${base}/api/order/status`, {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify({order_id:o.id, status})})
                          location.reload()
                        }}>Update</button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600">No orders yet.</div>
              )}
            </div>
          </section>
          <aside className="space-y-4">
            <div className="bg-white border rounded-lg shadow">
              <div className="border-b px-4 py-3"><h5 className="font-semibold">Restaurant Management</h5></div>
              <div className="p-4 space-y-2">
                <a href="/owner/menu/add" className="block text-center bg-blue-600 text-white px-3 py-2 rounded">Add Menu Item</a>
                {data.restaurant && (
                  <a href={`/restaurant/${data.restaurant.id}`} className="block text-center border border-blue-600 text-blue-700 px-3 py-2 rounded">View Menu</a>
                )}
              </div>
            </div>
            <div className="bg-white border rounded-lg shadow">
              <div className="border-b px-4 py-3"><h5 className="font-semibold">Menu Items ({data.menu_items?.length || 0})</h5></div>
              <div className="p-4 space-y-2">
                {data.menu_items && data.menu_items.length > 0 ? (
                  data.menu_items.map((m: any) => (
                    <div key={m.id} className="flex items-center justify-between border rounded p-2">
                      <div>
                        <div className="font-semibold">{m.name}</div>
                        <div className="text-sm text-gray-600">${m.price}</div>
                      </div>
                      <button className="text-red-600" onClick={async()=>{
                        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
                        await fetch(`${base}/api/menu/${m.id}/delete`, { method:'POST', credentials:'include' })
                        location.reload()
                      }}>Delete</button>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-600">No menu items yet.</div>
                )}
              </div>
            </div>
            <div className="bg-yellow-50 border rounded-lg p-4 text-yellow-900">
              <h6 className="font-semibold mb-1">Security Notice</h6>
              <p className="text-sm">The delete menu item functionality is intentionally vulnerable to CSRF attacks for educational purposes.</p>
            </div>
          </aside>
        </div>
      )}

      {data.role === 'admin' && (
        <div className="space-y-6">
          <div className="text-center bg-white rounded-b-2xl shadow border py-10">
            <h1 className="text-3xl font-bold mb-2">Admin Dashboard</h1>
            <p className="text-gray-700">VulnEats System Administration Panel</p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl shadow p-6 text-center">
              <div className="grid grid-cols-2">
                <div>
                  <div className="text-4xl font-bold">{data.restaurants?.length || 0}</div>
                  <div className="uppercase text-xs tracking-wide text-gray-600">Restaurants</div>
                </div>
                <div>
                  <div className="text-4xl font-bold">{data.orders?.length || 0}</div>
                  <div className="uppercase text-xs tracking-wide text-gray-600">Total Orders</div>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl shadow p-6">
              <h5 className="font-semibold mb-3">Quick Actions</h5>
               <div className="p-4 space-y-2">
                <a href="/admin/users" className="block w-full text-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
                  👥 Manage Users
                </a>
                <a href="/admin/restaurants/create" className="block w-full text-center bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500">
                  🏪 Create Restaurant
                </a>
              </div>
            </div>
          </div>

          {/* Restaurant creation moved to its own page at /admin/restaurants/create */}

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl shadow">
              <div className="border-b p-6"><h5 className="font-semibold">Restaurants</h5></div>
              <div className="p-6 max-h-[400px] overflow-y-auto space-y-3">
                {data.restaurants && data.restaurants.length > 0 ? (
                  data.restaurants.map((r: any) => (
                    <div key={r.id} className="bg-gray-50 rounded p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h6 className="font-semibold">{r.name}</h6>
                          <div className="text-sm text-gray-600">📍 {r.address}</div>
                          {r.created_at && <div className="text-sm text-gray-600">📅 {r.created_at}</div>}
                        </div>
                        <button 
                          onClick={async () => {
                            if (confirm(`Are you sure you want to delete "${r.name}"? This action cannot be undone.`)) {
                              setDeletingRestaurant(r.id)
                              try {
                                const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
                                const response = await fetch(`${base}/api/admin/restaurant/${r.id}/delete`, {
                                  method: 'POST',
                                  credentials: 'include'
                                })
                                
                                if (response.ok) {
                                  const result = await response.json()
                                  setCreateMessage({ type: 'success', text: result.message })
                                  // Refresh dashboard data after a short delay
                                  setTimeout(() => location.reload(), 1500)
                                } else {
                                  const error = await response.text()
                                  setCreateMessage({ type: 'error', text: `Error deleting restaurant: ${error}` })
                                }
                              } catch (error) {
                                setCreateMessage({ type: 'error', text: `Network error: ${error}` })
                              } finally {
                                setDeletingRestaurant(null)
                              }
                            }
                          }}
                          disabled={deletingRestaurant === r.id}
                          className={`ml-3 px-3 py-1 text-sm rounded focus:outline-none focus:ring-2 ${
                            deletingRestaurant === r.id
                              ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                              : 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                          }`}
                          title="Delete restaurant"
                        >
                          {deletingRestaurant === r.id ? '⏳ Deleting...' : '🗑️ Delete'}
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-600 py-6">No restaurants found.</div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow">
              <div className="border-b p-6"><h5 className="font-semibold">Recent Orders</h5></div>
              <div className="p-6 max-h-[400px] overflow-y-auto space-y-3">
                {data.orders && data.orders.length > 0 ? (
                  data.orders.slice(0, 5).map((o: any) => (
                    <div key={o.id} className="bg-gray-50 rounded p-3">
                      <div className="flex items-start justify-between mb-2">
                        <h6 className="font-semibold">Order #{o.id}</h6>
                        {statusBadge(o.status)}
                      </div>
                      <div className="text-sm text-gray-700 space-y-1">
                        <div>👤 {o.username}</div>
                        <div>🍽️ {o.restaurant_name}</div>
                        <div className="font-semibold">${o.total_amount}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-600 py-6">No orders found.</div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border p-6">
            <h5 className="font-semibold mb-2">Admin Features</h5>
            <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-700">
              <ul className="space-y-2">
                <li>✔️ View all restaurants and their details</li>
                <li>✔️ Monitor all orders across the system</li>
              </ul>
              <ul className="space-y-2">
                <li>✔️ Manage user accounts and permissions</li>
                <li>✔️ Access system logs for monitoring</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}


