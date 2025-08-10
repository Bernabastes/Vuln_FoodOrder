'use client'

import { useRef, useState } from 'react'

export default function CreateRestaurantPage() {
  const [isCreating, setIsCreating] = useState(false)
  const [createMessage, setCreateMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)
  const formRef = useRef<HTMLFormElement>(null)

  return (
    <main className="max-w-3xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow p-6">
        <div className="mb-4">
          <h1 className="text-2xl font-bold">Create Restaurant</h1>
          <p className="text-gray-600 text-sm">Create a new restaurant and owner account.</p>
        </div>

        {createMessage && (
          <div
            className={`mb-4 p-3 rounded-md ${
              createMessage.type === 'success'
                ? 'bg-green-100 text-green-800 border border-green-200'
                : 'bg-red-100 text-red-800 border border-red-200'
            }`}
          >
            {createMessage.text}
          </div>
        )}

        <form
          ref={formRef}
          onSubmit={async (e) => {
            e.preventDefault()
            setIsCreating(true)
            setCreateMessage(null)

            const formData = new FormData(e.currentTarget)

            try {
              const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
              const response = await fetch(`${base}/api/admin/restaurant/create`, {
                method: 'POST',
                credentials: 'include',
                body: formData
              })

              if (response.ok) {
                const result = await response.json()
                setCreateMessage({
                  type: 'success',
                  text: result.message || 'Restaurant created successfully!'
                })
                if (formRef.current) {
                  formRef.current.reset()
                }
              } else {
                const error = await response.text()
                setCreateMessage({ type: 'error', text: `Error creating restaurant: ${error}` })
              }
            } catch (error) {
              setCreateMessage({ type: 'error', text: `Network error: ${error}` as string })
            } finally {
              setIsCreating(false)
            }
          }}
          className="grid md:grid-cols-2 gap-4"
        >
          <div className="md:col-span-2">
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Restaurant Name *
            </label>
            <input
              type="text"
              id="name"
              name="name"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="md:col-span-2">
            <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-1">
              Address *
            </label>
            <input
              type="text"
              id="address"
              name="address"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Owner Username *
            </label>
            <input
              type="text"
              id="username"
              name="username"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Owner Email *
            </label>
            <input
              type="email"
              id="email"
              name="email"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="md:col-span-2">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Owner Password *
            </label>
            <input
              type="password"
              id="password"
              name="password"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">A new owner account will be created with these credentials</p>
          </div>

          <div>
            <label htmlFor="logo" className="block text-sm font-medium text-gray-700 mb-1">
              Poster Image (file) *
            </label>
            <input
              type="file"
              id="logo"
              name="logo"
              accept="image/*"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">Required. Upload an image to show on the restaurant card.</p>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
              disabled={isCreating}
            >
              {isCreating ? 'Creating...' : 'Create Restaurant'}
            </button>
          </div>
        </form>

        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <h6 className="font-semibold text-yellow-900 mb-1">Security Notice</h6>
          <p className="text-sm text-yellow-800">
            The restaurant creation functionality is intentionally vulnerable to CSRF attacks for educational purposes.
          </p>
        </div>
      </div>
    </main>
  )
}


