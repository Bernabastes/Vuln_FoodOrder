import { cookies } from 'next/headers'
import PlaceOrderButton from '../../components/PlaceOrderButton'
import BatchPlaceOrdersButton from '../../components/BatchPlaceOrdersButton'
import RemoveFromCartButton from '../../components/RemoveFromCartButton'

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
  // Group items by restaurant (include restaurant name)
  const groups: Record<string, { items: any[]; total: number; name?: string }> = {}
  for (const it of cart.items || []) {
    const rid = it.menu_item.restaurant_id
    const rname = it.menu_item.restaurant_name || `Restaurant #${rid}`
    if (!groups[rid]) groups[rid] = { items: [], total: 0, name: rname }
    groups[rid].items.push(it)
    groups[rid].total += it.total
    if (!groups[rid].name) groups[rid].name = rname
  }

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Your Cart</h1>
        {cart.items.length === 0 ? (
          <p>Your cart is empty.</p>
        ) : (
          <>
            {Object.entries(groups).map(([rid, g]: any, i) => (
              <div key={rid} className="mb-8">
                <h2 className="text-lg font-semibold mb-2">{g.name || `Restaurant #${rid}`}</h2>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b">
                      <th className="py-2">Item</th>
                      <th className="py-2">Qty</th>
                      <th className="py-2">Total</th>
                      <th className="py-2 text-right">Remove</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((ci: any, idx: number) => (
                      <tr key={idx} className="border-b">
                        <td className="py-2">{ci.menu_item.name}</td>
                        <td className="py-2">{ci.quantity}</td>
                        <td className="py-2">${ci.total}</td>
                        <td className="py-2 text-right">
                          <RemoveFromCartButton cartItemId={ci.cart_item_id} menuItemId={ci.menu_item.id} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td></td>
                      <td className="py-2 font-semibold text-right">Subtotal</td>
                      <td className="py-2 font-semibold">${g.total}</td>
                    </tr>
                  </tfoot>
                </table>
                <div className="mt-2 text-xs text-gray-700">
                  {g.items.map((ci: any, idx: number) => (
                    <div key={idx} className="mt-1">
                      <span className="text-gray-500">Special:</span>{' '}
                      <span
                        className="text-gray-900"
                        dangerouslySetInnerHTML={{ __html: ci.special_instructions || '' }}
                      />
                    </div>
                  ))}
                </div>
                <div className="text-right mt-4">
                  <PlaceOrderButton restaurantId={Number(rid)} />
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-600">Grand Total: ${cart.total}</div>
              <BatchPlaceOrdersButton />
            </div>
          </>
        )}
      </div>
    </main>
  )
}
