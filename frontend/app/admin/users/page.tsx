'use client'
import { useEffect, useState, useRef } from 'react'

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [isDeleting, setIsDeleting] = useState<number | null>(null)
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  const loadUsers = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      const res = await fetch(`${base}/api/admin/users`, { credentials: 'include' })
      if (res.ok) {
        const usersData = await res.json()
        setUsers(usersData)
      } else {
        setMessage({ type: 'error', text: 'Failed to load users' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Network error: ${error}` })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(userId)
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5001'
      const response = await fetch(`${base}/api/admin/user/${userId}/delete`, {
        method: 'POST',
        credentials: 'include'
      })
      
      if (response.ok) {
        const result = await response.json()
        setMessage({ type: 'success', text: result.message })
        // Refresh users list after successful deletion
        setTimeout(() => {
          loadUsers()
          setMessage(null)
        }, 1500)
      } else {
        const error = await response.text()
        setMessage({ type: 'error', text: `Error deleting user: ${error}` })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Network error: ${error}` })
    } finally {
      setIsDeleting(null)
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800'
      case 'owner': return 'bg-blue-100 text-blue-800'
      case 'customer': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (isLoading) {
    return (
      <main className="max-w-5xl mx-auto p-6">
        <div className="bg-white border rounded-lg shadow p-6">
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading users...</p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="bg-white border rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">User Management</h1>
          <button 
            onClick={loadUsers}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            🔄 Refresh
          </button>
        </div>

        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> Admin users are protected from deletion to maintain system security.
          </p>
        </div>

        {message && (
          <div className={`mb-4 p-3 rounded-md ${
            message.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-800' 
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            {message.text}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b bg-gray-50">
                <th className="py-3 px-4 font-semibold">#</th>
                <th className="py-3 px-4 font-semibold">Username</th>
                <th className="py-3 px-4 font-semibold">Email</th>
                <th className="py-3 px-4 font-semibold">Role</th>
                <th className="py-3 px-4 font-semibold">Created</th>
                <th className="py-3 px-4 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono">{user.id}</td>
                  <td className="py-3 px-4 font-medium">{user.username}</td>
                  <td className="py-3 px-4">{user.email}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getRoleBadgeColor(user.role)}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600">
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </td>
                  <td className="py-3 px-4">
                    {user.role === 'admin' ? (
                      <span className="text-gray-500 text-xs italic">Protected</span>
                    ) : (
                      <button 
                        onClick={() => handleDeleteUser(user.id, user.username)}
                        disabled={isDeleting === user.id}
                        className={`px-3 py-1 text-sm rounded focus:outline-none focus:ring-2 ${
                          isDeleting === user.id
                            ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                            : 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                        }`}
                        title="Delete user"
                      >
                        {isDeleting === user.id ? '⏳ Deleting...' : '🗑️ Delete'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {users.length === 0 && (
          <div className="text-center py-8 text-gray-600">
            No users found.
          </div>
        )}
      </div>
    </main>
  )
}


