'use client'
import { useState } from 'react'

export default function AddMenuItemPage() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    const form = new FormData()
    form.append('name', name)
    form.append('description', description)
    form.append('price', price)
    if (image) form.append('image', image)
    const res = await fetch(`${base}/api/menu/add`, { method: 'POST', credentials: 'include', body: form })
    if (res.ok) {
      setMessage('Added!')
    } else {
      setMessage('Failed')
    }
  }

  return (
    <main className="max-w-xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Add Menu Item</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="block text-sm mb-1">Name</label>
            <input className="w-full border rounded p-2" placeholder="Name" value={name} onChange={e=>setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Description</label>
            <textarea className="w-full border rounded p-2" placeholder="Description" value={description} onChange={e=>setDescription(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Price</label>
            <input className="w-full border rounded p-2" placeholder="Price" value={price} onChange={e=>setPrice(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Image</label>
            <input className="w-full" type="file" onChange={e=>setImage(e.target.files?.[0] || null)} />
          </div>
          <button className="w-full bg-blue-600 text-white px-4 py-2 rounded" type="submit">Save</button>
          {message && <div className="text-sm">{message}</div>}
        </form>
      </div>
    </main>
  )
}


