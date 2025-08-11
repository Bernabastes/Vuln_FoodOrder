'use client'
import { useRef, useState } from 'react'

export default function AddMenuItemPage() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setMessage(null)
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
    const form = new FormData()
    form.append('name', name)
    form.append('description', description)
    form.append('price', price)
    if (image) form.append('image', image)

    try {
      const res = await fetch(`${base}/api/menu/add`, { method: 'POST', credentials: 'include', body: form })
      if (res.ok) {
        setMessage({ type: 'success', text: 'Menu item added successfully!' })
        // Reset form fields
        setName('')
        setDescription('')
        setPrice('')
        setImage(null)
        if (formRef.current) formRef.current.reset()
      } else {
        const errorText = await res.text()
        setMessage({ type: 'error', text: errorText || 'Failed to add menu item' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="max-w-xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-4">Add Menu Item</h1>
        <form ref={formRef} onSubmit={onSubmit} className="space-y-3" aria-busy={isSaving}>
          <div>
            <label className="block text-sm mb-1">Name</label>
            <input className="w-full border rounded p-2" placeholder="Name" value={name} onChange={e=>setName(e.target.value)} disabled={isSaving} />
          </div>
          <div>
            <label className="block text-sm mb-1">Description</label>
            <textarea className="w-full border rounded p-2" placeholder="Description" value={description} onChange={e=>setDescription(e.target.value)} disabled={isSaving} />
          </div>
          <div>
            <label className="block text-sm mb-1">Price</label>
            <input className="w-full border rounded p-2" placeholder="Price" value={price} onChange={e=>setPrice(e.target.value)} disabled={isSaving} />
          </div>
          <div>
            <label className="block text-sm mb-1">Image</label>
            <input className="w-full" type="file" onChange={e=>setImage(e.target.files?.[0] || null)} disabled={isSaving} />
          </div>
          <button className="w-full bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2" type="submit" disabled={isSaving}>
            {isSaving && (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-r-transparent" />
            )}
            {isSaving ? 'Saving…' : 'Save'}
          </button>
          {message && (
            <div
              role="alert"
              className={`text-sm p-2 rounded border ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-800 border-green-200'
                  : 'bg-red-50 text-red-800 border-red-200'
              }`}
            >
              {message.text}
            </div>
          )}
        </form>
      </div>
    </main>
  )
}


