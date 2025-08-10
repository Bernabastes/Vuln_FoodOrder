import Link from 'next/link'
import AddToCartForm from '../../../components/AddToCartForm'

async function fetchMenu(id: string) {
  const base = process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  const res = await fetch(`${base}/api/restaurant/${id}/menu`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function RestaurantPage({ params }: { params: { id: string } }) {
  const data = await fetchMenu(params.id)
  if (!data) return <main className="p-6">Not found</main>
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <nav className="text-sm" aria-label="breadcrumb">
        <ol className="flex gap-2 text-gray-600">
          <li><Link className="hover:underline" href="/restaurants">Restaurants</Link></li>
          <li>/</li>
          <li className="text-gray-900">{data.restaurant.name}</li>
        </ol>
      </nav>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{data.restaurant.name}</h1>
          <p className="text-sm text-gray-600"><span className="inline-block mr-1">📍</span>{data.restaurant.address}</p>
        </div>
        <div>
          <Link className="border border-blue-600 text-blue-700 px-4 py-2 rounded" href="/cart">View Cart</Link>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.menu_items.map((m: any) => (
          <div key={m.id} className="rounded-lg border bg-white shadow-sm overflow-hidden">
            {m.image_path ? (
              <img
                src={`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'}/api/uploads/${m.image_path}`}
                alt={m.name}
                className="h-48 w-full object-cover"
              />
            ) : (
              <div className="bg-gray-100 h-48 flex items-center justify-center">
                <span className="text-gray-400">No image</span>
              </div>
            )}
            <div className="p-4">
              <div className="font-semibold">{m.name}</div>
              <div className="text-sm text-gray-700">{m.description}</div>
              <div className="mt-1 font-medium">{`$${Number(m.price).toFixed(2)}`}</div>
              <AddToCartForm menuItemId={m.id} />
            </div>
          </div>
        ))}
      </div>
      <Link className="inline-block mt-2 text-blue-600 underline" href="/cart">Go to cart</Link>
    </main>
  )
}


