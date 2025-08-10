import { cookies } from 'next/headers'
import PlaceOrderButton from '../../components/PlaceOrderButton'

async function fetchCart() {
  let base =
    process.env.INTERNAL_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE ||
    'http://localhost:5001'

  const cookieHeader = cookies().toString()

  const res = await fetch(`${base}/api/cart`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: 'no-store',
  })
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

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
                    <td className="py-2">${ci.total}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td></td>
                  <td className="py-2 font-semibold text-right">Grand Total</td>
                  <td className="py-2 font-semibold">${cart.total}</td>
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
