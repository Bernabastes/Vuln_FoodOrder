import sqlite3
import os
from config import Config

# Optional: Use Postgres if DATABASE_URL is provided
try:
    import psycopg
except Exception:
    psycopg = None  # type: ignore


def init_database():
    database_url = os.environ.get('DATABASE_URL')
    use_postgres = bool(database_url and psycopg is not None)
    if use_postgres:
        # Initialize Postgres schema
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('customer', 'admin', 'owner')),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS restaurants (
                        id SERIAL PRIMARY KEY,
                        owner_id INTEGER NOT NULL REFERENCES users(id),
                        name TEXT NOT NULL,
                        address TEXT NOT NULL,
                        logo_path TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS menu_items (
                        id SERIAL PRIMARY KEY,
                        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
                        name TEXT NOT NULL,
                        description TEXT,
                        price REAL NOT NULL,
                        image_path TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
                        total_amount REAL NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('pending', 'cooking', 'delivered', 'cancelled')),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS order_items (
                        id SERIAL PRIMARY KEY,
                        order_id INTEGER NOT NULL REFERENCES orders(id),
                        menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
                        quantity INTEGER NOT NULL,
                        special_instructions TEXT
                    )
                ''')

                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_restaurants_owner ON restaurants(owner_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_restaurant ON orders(restaurant_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)')

                # Unified cart: single table keyed by user_id
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cart_items (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
                        quantity INTEGER NOT NULL,
                        special_instructions TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id)')

                conn.commit()
        print("Database initialized in Postgres at", database_url)
        return

    # Fallback: SQLite local init
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'admin', 'owner')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
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
        CREATE TABLE IF NOT EXISTS menu_items (
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
        CREATE TABLE IF NOT EXISTS orders (
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
        CREATE TABLE IF NOT EXISTS order_items (
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

    # Unified cart: single table keyed by user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            special_instructions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id)')

    conn.commit()
    conn.close()
    print("Database initialized at", Config.DATABASE_PATH)


if __name__ == '__main__':
    init_database()


