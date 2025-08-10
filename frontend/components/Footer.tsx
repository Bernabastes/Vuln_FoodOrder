export default function Footer() {
  return (
    <footer className="mt-10 bg-gray-900 text-gray-200">
      <div className="max-w-6xl mx-auto px-4 py-8 grid md:grid-cols-2 gap-6">
        <div>
          <h5 className="text-lg font-semibold">VulnEats</h5>
          <p className="text-sm text-gray-400">Your favorite food ordering platform</p>
        </div>
        <div className="text-right text-sm text-gray-400">
          <p>© 2024 VulnEats. All rights reserved.</p>
          <p className="opacity-70">Cybersecurity Lab Project</p>
        </div>
      </div>
    </footer>
  )
}


