import sqlite3
import hashlib
import os
from config import Config


def init_database():
    if os.path.exists(Config.DATABASE_PATH):
        os.remove(Config.DATABASE_PATH)

    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'admin', 'owner')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            logo_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'cooking', 'delivered', 'cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            special_instructions TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        )
    ''')

    cursor.execute('CREATE INDEX idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX idx_restaurants_owner ON restaurants(owner_id)')
    cursor.execute('CREATE INDEX idx_menu_items_restaurant ON menu_items(restaurant_id)')
    cursor.execute('CREATE INDEX idx_orders_user ON orders(user_id)')
    cursor.execute('CREATE INDEX idx_orders_restaurant ON orders(restaurant_id)')
    cursor.execute('CREATE INDEX idx_order_items_order ON order_items(order_id)')

    users_data = [
        ('admin', 'admin@vulneats.com', hashlib.md5('admin123'.encode()).hexdigest(), 'admin'),
        ('restaurant1', 'restaurant1@vulneats.com', hashlib.md5('password123'.encode()).hexdigest(), 'owner'),
        ('restaurant2', 'restaurant2@vulneats.com', hashlib.md5('password123'.encode()).hexdigest(), 'owner'),
        ('customer1', 'customer1@vulneats.com', hashlib.md5('password123'.encode()).hexdigest(), 'customer'),
        ('customer2', 'customer2@vulneats.com', hashlib.md5('password123'.encode()).hexdigest(), 'customer'),
        ('customer3', 'customer3@vulneats.com', hashlib.md5('password123'.encode()).hexdigest(), 'customer'),
    ]
    cursor.executemany('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)', users_data)

    restaurants_data = [
        (2, 'Pizza Palace', '123 Main St, City Center', 'pizza_palace_logo.png'),
        (3, 'Burger House', '456 Oak Ave, Downtown', 'burger_house_logo.png'),
    ]
    cursor.executemany('INSERT INTO restaurants (owner_id, name, address, logo_path) VALUES (?, ?, ?, ?)', restaurants_data)

    menu_items_data = [
        (1, 'Margherita Pizza', 'Classic tomato sauce with mozzarella cheese', 12.99, 'margherita.jpg'),
        (1, 'Pepperoni Pizza', 'Spicy pepperoni with melted cheese', 14.99, 'pepperoni.jpg'),
        (1, 'Hawaiian Pizza', 'Ham and pineapple with cheese', 13.99, 'hawaiian.jpg'),
        (1, 'Supreme Pizza', 'Loaded with vegetables and meats', 16.99, 'supreme.jpg'),
        (2, 'Classic Burger', 'Beef patty with lettuce, tomato, and cheese', 8.99, 'classic_burger.jpg'),
        (2, 'Cheeseburger', 'Beef patty with melted cheese', 9.99, 'cheeseburger.jpg'),
        (2, 'Bacon Burger', 'Beef patty with crispy bacon', 11.99, 'bacon_burger.jpg'),
        (2, 'Veggie Burger', 'Plant-based patty with fresh vegetables', 10.99, 'veggie_burger.jpg'),
    ]
    cursor.executemany('INSERT INTO menu_items (restaurant_id, name, description, price, image_path) VALUES (?, ?, ?, ?, ?)', menu_items_data)

    orders_data = [
        (4, 1, 25.98, 'delivered', '2024-01-15 12:30:00'),
        (5, 1, 29.97, 'cooking', '2024-01-15 13:45:00'),
        (6, 2, 19.98, 'pending', '2024-01-15 14:20:00'),
    ]
    cursor.executemany('INSERT INTO orders (user_id, restaurant_id, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?)', orders_data)

    order_items_data = [
        (1, 1, 2, 'Extra cheese please'),
        (2, 2, 1, 'No pineapple'),
        (2, 3, 1, 'Well done'),
        (3, 5, 2, 'Medium rare'),
    ]
    cursor.executemany('INSERT INTO order_items (order_id, menu_item_id, quantity, special_instructions) VALUES (?, ?, ?, ?)', order_items_data)

    conn.commit()
    conn.close()
    print("Database initialized at", Config.DATABASE_PATH)


if __name__ == '__main__':
    init_database()


