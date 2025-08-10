export const metadata = {
  title: 'VulnEats',
  description: 'Food ordering demo (Next.js frontend)'
}

import './globals.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <NavBar />
        {children}
        <Footer />
      </body>
    </html>
  )
}


