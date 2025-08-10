'use client'
import { useState } from 'react'

export default function AddToCartForm({ menuItemId }: { menuItemId: number }) {
  const [quantity, setQuantity] = useState(1)
  const [special, setSpecial] = useState('')
  const [saving, setSaving] = useState(false)

  const add = async () => {
    setSaving(true)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    await fetch(`${base}/api/cart/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ menu_item_id: menuItemId, quantity, special_instructions: special })
    })
    setSaving(false)
  }

  return (
    <div className="mt-2 flex items-center gap-2">
      <input
        type="number"
        min={1}
        value={quantity}
        onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
        className="w-20 border rounded p-2"
      />
      <input
        placeholder="Special instructions"
        value={special}
        onChange={(e) => setSpecial(e.target.value)}
        className="flex-1 border rounded p-2"
      />
      <button onClick={add} disabled={saving} className="bg-green-600 text-white px-3 py-2 rounded">
        {saving ? 'Adding...' : 'Add'}
      </button>
    </div>
  )
}


