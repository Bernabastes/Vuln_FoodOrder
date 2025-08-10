from flask import Flask, request, session, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import os
from datetime import timedelta
from werkzeug.utils import secure_filename

# Optional Postgres and Cloudinary support
try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # psycopg may not be installed yet
    psycopg = None  # type: ignore
    dict_row = None  # type: ignore

try:
    import cloudinary
    import cloudinary.uploader
except Exception:
    cloudinary = None  # type: ignore


class ApiConfig:
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/vulneats.db")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY", "vulneats-secret-key-change-in-production")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/app/uploads")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(ApiConfig)
    CORS(app, supports_credentials=True)

    os.makedirs(ApiConfig.UPLOAD_FOLDER, exist_ok=True)

    # Configure Cloudinary if available
    if cloudinary is not None:
        cloudinary_url = os.environ.get("CLOUDINARY_URL")
        if cloudinary_url:
            cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
        else:
            cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
            api_key = os.environ.get("CLOUDINARY_API_KEY")
            api_secret = os.environ.get("CLOUDINARY_API_SECRET")
            if cloud_name and api_key and api_secret:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    secure=True,
                )

    use_postgres = bool(ApiConfig.DATABASE_URL and psycopg is not None)

    class DatabaseConnection:
        def __init__(self, conn, is_postgres: bool):
            self._conn = conn
            self._is_pg = is_postgres

        def execute(self, sql: str, params=()):
            if self._is_pg:
                sql = sql.replace("?", "%s")
                return self._conn.execute(sql, params)
            return self._conn.execute(sql, params)

        def commit(self):
            return self._conn.commit()

        def close(self):
            return self._conn.close()

    def get_db_connection():
        if use_postgres:
            conn = psycopg.connect(ApiConfig.DATABASE_URL, row_factory=dict_row)
            return DatabaseConnection(conn, True)
        conn = sqlite3.connect(ApiConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return DatabaseConnection(conn, False)

    def insert_and_get_id(conn: DatabaseConnection, insert_sql: str, params) -> int:
        if use_postgres:
            cur = conn.execute(insert_sql + " RETURNING id", params)
            row = cur.fetchone()
            if row is None:
                return 0
            return int(row["id"]) if isinstance(row, dict) else int(row[0])
        cur = conn.execute(insert_sql, params)
        try:
            return int(cur.lastrowid)
        except Exception:
            row = conn.execute("SELECT last_insert_rowid() AS id").fetchone()
            return int(row["id"]) if row else 0

    # NOTE: get_db_connection redefined above to support Postgres

    def login_required_json(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "auth_required"}), 401
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    def admin_required_json(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "auth_required"}), 401
            conn = get_db_connection()
            user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
            if not user or user['role'] != 'admin':
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    def owner_required_json(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "auth_required"}), 401
            conn = get_db_connection()
            user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
            if not user or user['role'] not in ('admin', 'owner'):
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    @app.post("/api/login")
    def api_login():
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        password_hash = hashlib.md5(password.encode()).hexdigest()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash),
        ).fetchone()
        conn.close()

        if not user:
            return jsonify({"ok": False, "message": "Invalid credentials"}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"ok": True, "user": {"id": user["id"], "username": user["username"], "role": user["role"]}})

    @app.post("/api/register")
    def api_register():
        data = request.get_json() or {}
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")
        password_hash = hashlib.md5(password.encode()).hexdigest()

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, "customer"),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"ok": False, "message": "Username or email exists"}), 400
        finally:
            conn.close()

        return jsonify({"ok": True})

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/restaurants")
    def api_restaurants():
        conn = get_db_connection()
        rows = conn.execute("SELECT id, name, address, logo_path FROM restaurants").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/restaurant/<int:restaurant_id>/menu")
    def api_restaurant_menu(restaurant_id: int):
        conn = get_db_connection()
        restaurant = conn.execute("SELECT id, name, address, logo_path FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        items = conn.execute(
            "SELECT id, name, description, price, image_path FROM menu_items WHERE restaurant_id = ?",
            (restaurant_id,),
        ).fetchall()
        conn.close()
        return jsonify({"restaurant": dict(restaurant), "menu_items": [dict(i) for i in items]})

    @app.get("/api/search")
    def api_search():
        query = request.args.get("q", "")
        conn = get_db_connection()
        # Keep parity with current behavior (vulnerable LIKE). We'll parameterize but still allow wildcards.
        rows = conn.execute(
            "SELECT id, restaurant_id, name, description, price, image_path FROM menu_items WHERE name LIKE ? OR description LIKE ?",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/me")
    def api_me():
        if "user_id" not in session:
            return jsonify({"user": None})
        return jsonify({
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "role": session.get("role"),
            }
        })

    @app.get("/api/dashboard")
    @login_required_json
    def api_dashboard():
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        role = user['role'] if user else 'customer'
        if role == 'admin':
            restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
            orders = conn.execute('''
                SELECT o.*, u.username, r.name as restaurant_name
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN restaurants r ON o.restaurant_id = r.id
                ORDER BY o.created_at DESC
            ''').fetchall()
            conn.close()
            return jsonify({
                'role': 'admin',
                'restaurants': [dict(r) for r in restaurants],
                'orders': [dict(o) for o in orders]
            })
        elif role == 'owner':
            restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
            if restaurant:
                orders = conn.execute('''
                    SELECT o.*, u.username FROM orders o
                    JOIN users u ON o.user_id = u.id
                    WHERE o.restaurant_id = ?
                    ORDER BY o.created_at DESC
                ''', (restaurant['id'],)).fetchall()
                menu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant['id'],)).fetchall()
                conn.close()
                return jsonify({
                    'role': 'owner',
                    'restaurant': dict(restaurant),
                    'orders': [dict(o) for o in orders],
                    'menu_items': [dict(m) for m in menu_items],
                })
            conn.close()
            return jsonify({'role': 'owner', 'error': 'no_restaurant'})
        else:
            orders = conn.execute('''
                SELECT o.*, r.name as restaurant_name FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
            ''', (session['user_id'],)).fetchall()
            restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
            conn.close()
            return jsonify({
                'role': 'customer',
                'orders': [dict(o) for o in orders],
                'restaurants': [dict(r) for r in restaurants],
            })

    @app.post('/api/cart/add')
    @login_required_json
    def api_cart_add():
        data = request.get_json() or {}
        menu_item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        special_instructions = data.get('special_instructions', '')
        if 'cart' not in session:
            session['cart'] = []
        session['cart'].append({
            'menu_item_id': menu_item_id,
            'quantity': quantity,
            'special_instructions': special_instructions,
        })
        return jsonify({'ok': True})

    @app.get('/api/cart')
    @login_required_json
    def api_cart_view():
        if 'cart' not in session or not session['cart']:
            return jsonify({'items': [], 'total': 0})
        conn = get_db_connection()
        cart_items = []
        total = 0
        for item in session['cart']:
            menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item['menu_item_id'],)).fetchone()
            if menu_item:
                item_total = menu_item['price'] * int(item['quantity'])
                total += item_total
                cart_items.append({
                    'menu_item': dict(menu_item),
                    'quantity': item['quantity'],
                    'special_instructions': item['special_instructions'],
                    'total': item_total,
                })
        conn.close()
        return jsonify({'items': cart_items, 'total': total})

    @app.post('/api/orders/place')
    @login_required_json
    def api_place_order():
        if 'cart' not in session or not session['cart']:
            return jsonify({'ok': False, 'message': 'empty_cart'}), 400
        data = request.get_json() or {}
        restaurant_id = data.get('restaurant_id')
        conn = get_db_connection()
        total = 0
        for item in session['cart']:
            menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item['menu_item_id'],)).fetchone()
            if menu_item:
                total += menu_item['price'] * int(item['quantity'])
        order_id = insert_and_get_id(
            conn,
            '''
            INSERT INTO orders (user_id, restaurant_id, total_amount, status)
            VALUES (?, ?, ?, ?)
            ''',
            (session['user_id'], restaurant_id, total, 'pending')
        )
        for item in session['cart']:
            conn.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, special_instructions)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item['menu_item_id'], item['quantity'], item['special_instructions']))
        conn.commit()
        conn.close()
        session.pop('cart', None)
        return jsonify({'ok': True, 'order_id': order_id})

    @app.post('/api/order/status')
    @owner_required_json
    def api_update_order_status():
        data = request.get_json() or {}
        order_id = data.get('order_id')
        status = data.get('status')
        conn = get_db_connection()
        # Ensure owner owns the restaurant for the order
        row = conn.execute('''
            SELECT r.owner_id FROM orders o JOIN restaurants r ON o.restaurant_id = r.id WHERE o.id = ?
        ''', (order_id,)).fetchone()
        if not row or row['owner_id'] != session['user_id']:
            conn.close()
            return jsonify({'error': 'forbidden'}), 403
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    @app.post('/api/menu/add')
    @owner_required_json
    def api_add_menu_item():
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Prefer Cloudinary if configured; fallback to local if upload fails
                image_path = None
                use_cloud = (
                    cloudinary is not None and (
                        os.environ.get('CLOUDINARY_URL') or (
                            os.environ.get('CLOUDINARY_CLOUD_NAME') and
                            os.environ.get('CLOUDINARY_API_KEY') and
                            os.environ.get('CLOUDINARY_API_SECRET')
                        )
                    )
                )
                if use_cloud:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder='vulneats/menu_items',
                            resource_type='image',
                        )
                        image_path = upload_result.get('secure_url') or upload_result.get('url')
                        print('Cloudinary upload result:', upload_result)
                    except Exception as e:
                        print('Cloudinary upload failed:', e)
                        image_path = None
                if not image_path:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(ApiConfig.UPLOAD_FOLDER, filename))
                    image_path = filename
                    print('Saved image locally as:', image_path)

        
        conn = get_db_connection()
        restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
        
        if not restaurant:
            conn.close()
            return jsonify({'error': 'no_restaurant'}), 400
        
        print('Inserting menu item with image_path:', image_path)
        conn.execute('''
            INSERT INTO menu_items (restaurant_id, name, description, price, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (restaurant['id'], name, description, price, image_path))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    @app.post('/api/menu/<int:item_id>/delete')
    @owner_required_json
    def api_delete_menu_item(item_id: int):
        conn = get_db_connection()
        restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
        if restaurant:
            conn.execute('DELETE FROM menu_items WHERE id = ? AND restaurant_id = ?', (item_id, restaurant['id']))
            conn.commit()
        conn.close()
        return jsonify({'ok': True})

    @app.get('/api/uploads/<path:filename>')
    def api_uploaded_file(filename: str):
        # Mimic original behavior (no extra validation)
        from flask import send_from_directory
        return send_from_directory(ApiConfig.UPLOAD_FOLDER, filename)

    @app.get('/api/admin/users')
    @admin_required_json
    def api_admin_users():
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(u) for u in users])

    @app.get('/api/admin/logs')
    @admin_required_json
    def api_admin_logs():
        log_file = request.args.get('file', '/var/log/apache2/access.log')
        try:
            with open(log_file, 'r') as f:
                logs = f.readlines()[-100:]
        except Exception:
            logs = ['Error reading log file']
        return jsonify({'lines': logs})

    @app.post('/api/admin/restaurant/create')
    @admin_required_json
    def api_admin_create_restaurant():
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        address = data.get('address', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not name or not address:
            return jsonify({'error': 'Name and address are required'}), 400
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        conn = get_db_connection()
        try:
            # Check if username or email already exists
            existing_user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
            if existing_user:
                conn.close()
                return jsonify({'error': 'Username or email already exists'}), 400
            
            # Create new owner user
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            owner_id = insert_and_get_id(
                conn,
                '''
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, 'owner', CURRENT_TIMESTAMP)
                ''',
                (username, email, hashed_password)
            )

            # Create the restaurant
            restaurant_id = insert_and_get_id(
                conn,
                '''
                INSERT INTO restaurants (owner_id, name, address, logo_path, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (owner_id, name, address, None)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                'ok': True, 
                'restaurant_id': restaurant_id,
                'owner_id': owner_id,
                'message': f'Restaurant "{name}" created successfully with owner "{username}"'
            })
            
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500


    @app.post('/api/admin/restaurant/<int:restaurant_id>/delete')
    @admin_required_json
    def api_admin_delete_restaurant(restaurant_id: int):
        conn = get_db_connection()
        try:
            # Check if restaurant exists
            restaurant = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
            if not restaurant:
                conn.close()
                return jsonify({'error': 'Restaurant not found'}), 404
            
            # Check if restaurant has any orders
            orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE restaurant_id = ?', (restaurant_id,)).fetchone()
            if orders['count'] > 0:
                conn.close()
                return jsonify({'error': 'Cannot delete restaurant with existing orders'}), 400
            
            # Check if restaurant has any menu items
            menu_items = conn.execute('SELECT COUNT(*) as count FROM menu_items WHERE restaurant_id = ?', (restaurant_id,)).fetchone()
            if menu_items['count'] > 0:
                conn.close()
                return jsonify({'error': 'Cannot delete restaurant with existing menu items'}), 400
            
            # Delete the restaurant
            conn.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'ok': True,
                'message': f'Restaurant "{restaurant["name"]}" deleted successfully'
            })
            
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

    @app.post('/api/admin/user/<int:user_id>/delete')
    @admin_required_json
    def api_admin_delete_user(user_id: int):
        conn = get_db_connection()
        try:
            # Check if user exists
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                conn.close()
                return jsonify({'error': 'User not found'}), 404
            
            # Prevent admin from deleting themselves
            if user_id == session['user_id']:
                conn.close()
                return jsonify({'error': 'Cannot delete your own account'}), 400
            
            # Prevent deletion of admin users
            if user['role'] == 'admin':
                conn.close()
                return jsonify({'error': 'Cannot delete admin users'}), 400
            
            # Check if user has any restaurants
            restaurants = conn.execute('SELECT COUNT(*) as count FROM restaurants WHERE owner_id = ?', (user_id,)).fetchone()
            if restaurants['count'] > 0:
                conn.close()
                return jsonify({'error': 'Cannot delete user with existing restaurants'}), 400
            
            # Check if user has any orders
            orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE user_id = ?', (user_id,)).fetchone()
            if orders['count'] > 0:
                conn.close()
                return jsonify({'error': 'Cannot delete user with existing orders'}), 400
            
            # Delete the user
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'ok': True,
                'message': f'User "{user["username"]}" deleted successfully'
            })
            
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)


