'use client'

import { useState } from 'react'

type PlaceOrderButtonProps = {
  restaurantId: number
}

export default function PlaceOrderButton({ restaurantId }: PlaceOrderButtonProps) {
  const [isPlacing, setIsPlacing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const placeOrder = async () => {
    setIsPlacing(true)
    setErrorMessage(null)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'

    try {
      // Try payment checkout first (handles creating the order if only restaurant_id is given)
      const checkoutRes = await fetch(`${base}/api/payments/chapa/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ restaurant_id: restaurantId })
      })

      if (checkoutRes.status === 401) {
        window.location.href = '/login?next=/cart'
        return
      }

      if (checkoutRes.ok) {
        const data = await checkoutRes.json()
        if (data?.ok && data.checkout_url) {
          window.location.href = data.checkout_url
          return
        }
        if (data?.ok && data.order_id) {
          // Payment not configured, but order created
          window.location.href = '/dashboard'
          return
        }
      }

      // Fallback: directly place order without payment integration
      const placeRes = await fetch(`${base}/api/orders/place`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ restaurant_id: restaurantId })
      })

      if (placeRes.status === 401) {
        window.location.href = '/login?next=/cart'
        return
      }

      if (placeRes.ok) {
        const data = await placeRes.json()
        if (data?.ok) {
          window.location.href = '/dashboard'
          return
        }
      }

      setErrorMessage('Failed to place order. Please try again.')
    } catch (err) {
      setErrorMessage('Network error. Please try again.')
    } finally {
      setIsPlacing(false)
    }
  }

  return (
    <div className="inline-flex flex-col items-end gap-1">
      <button
        onClick={placeOrder}
        disabled={isPlacing}
        className={`px-4 py-2 rounded-lg font-semibold shadow text-white transition-colors ${
          isPlacing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isPlacing ? 'Placing…' : 'Place Order'}
      </button>
      {errorMessage && (
        <div className="text-xs text-red-700 bg-red-100 border border-red-200 rounded px-2 py-1">
          {errorMessage}
        </div>
      )}
    </div>
  )
}


