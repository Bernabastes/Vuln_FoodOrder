'use client'

export default function RemoveFromCartButton({ cartItemId, menuItemId }: { cartItemId?: number; menuItemId?: number }) {
  async function removeItem() {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    await fetch(`${base}/api/cart/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ cart_item_id: cartItemId, menu_item_id: menuItemId })
    })
    location.reload()
  }
  return (
    <button
      onClick={removeItem}
      aria-label="Remove"
      className="text-red-600 hover:text-red-800"
      title="Remove"
    >
      ✕
    </button>
  )
}


