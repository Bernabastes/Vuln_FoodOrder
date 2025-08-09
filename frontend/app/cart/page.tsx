async function fetchCart() {
  // Use INTERNAL_API_BASE for server-side, NEXT_PUBLIC_API_BASE for client-side
  let base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
  if (typeof window === 'undefined' && process.env.INTERNAL_API_BASE) {
    base = process.env.INTERNAL_API_BASE
  }
  const res = await fetch(`${base}/api/cart`, { cache: 'no-store', credentials: 'include' as any })
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

import PlaceOrderButton from '../../components/PlaceOrderButton'

export default async function CartPage() {
  const cart = await fetchCart()
  const restaurantId = cart.items?.[0]?.menu_item?.restaurant_id
  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Your Cart</h1>
        {cart.items.length === 0 ? (
          <p>Your cart is empty.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="py-2">Item</th>
                  <th className="py-2">Qty</th>
                  <th className="py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {cart.items.map((ci: any, idx: number) => (
                  <tr key={idx} className="border-b">
                    <td className="py-2">{ci.menu_item.name}</td>
                    <td className="py-2">{ci.quantity}</td>
                    <td className="py-2">${'{'}ci.total{'}'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td></td>
                  <td className="py-2 font-semibold text-right">Grand Total</td>
                  <td className="py-2 font-semibold">${'{'}cart.total{'}'}</td>
                </tr>
              </tfoot>
            </table>
            <div className="text-right mt-4">
              <PlaceOrderButton restaurantId={restaurantId} />
            </div>
          </>
        )}
      </div>
    </main>
  )
}


