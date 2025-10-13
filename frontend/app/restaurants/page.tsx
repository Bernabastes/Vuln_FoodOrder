import RestaurantsList from '../../components/RestaurantsList'

export default function RestaurantsPage() {
  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Our Restaurants</h1>
        <p className="text-gray-600">Discover amazing restaurants and their delicious menus</p>
      </div>
      <RestaurantsList />
    </main>
  )
}


