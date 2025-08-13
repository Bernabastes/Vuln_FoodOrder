'use client'
import { useState } from 'react'

export default function BatchPlaceOrdersButton() {
  const [isPlacing, setIsPlacing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const placeAll = async () => {
    setIsPlacing(true)
    setErrorMessage(null)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    try {
      // Initiate batch payment checkout (will create orders per restaurant as needed)
      const res = await fetch(`${base}/api/payments/chapa/checkout/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })

      if (res.status === 401) {
        window.location.href = '/login?next=/cart'
        return
      }

      if (!res.ok) {
        setErrorMessage('Failed to place orders. Please try again.')
        return
      }
      const data = await res.json()
      if (data?.ok && Array.isArray(data.payments) && data.payments.length > 0) {
        // Redirect current tab to the first Chapa checkout page
        const first = data.payments.find((p: any) => p.checkout_url)
        if (first?.checkout_url) {
          window.location.href = first.checkout_url
          return
        }
      }
      setErrorMessage('Failed to place orders. Please try again.')
    } catch (e) {
      setErrorMessage('Network error. Please try again.')
    } finally {
      setIsPlacing(false)
    }
  }

  return (
    <div className="inline-flex flex-col items-end gap-1">
      <button
        onClick={placeAll}
        disabled={isPlacing}
        className={`px-4 py-2 rounded-lg font-semibold shadow text-white transition-colors ${
          isPlacing ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
        }`}
      >
        {isPlacing ? 'Placing all…' : 'Place all orders'}
      </button>
      {errorMessage && (
        <div className="text-xs text-red-700 bg-red-100 border border-red-200 rounded px-2 py-1">
          {errorMessage}
        </div>
      )}
    </div>
  )
}


