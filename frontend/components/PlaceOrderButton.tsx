'use client'
export default function PlaceOrderButton({ restaurantId }: { restaurantId?: number }) {
  return (
    <button
      className="bg-blue-600 text-white px-4 py-2 rounded"
      onClick={async () => {
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
        // Try to infer restaurantId from cart if not provided
        let payload: any = {}
        if (!restaurantId) {
          try {
            const res = await fetch(`${base}/api/cart`, { credentials: 'include' })
            if (res.ok) {
              const cart = await res.json()
              payload.restaurant_id = cart.items?.[0]?.menu_item?.restaurant_id
            }
          } catch {}
        } else {
          payload.restaurant_id = restaurantId
        }
        if (!payload.restaurant_id) return
        await fetch(`${base}/api/orders/place`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        })
        location.href = '/dashboard'
      }}
    >
      Place order
    </button>
  )
}


