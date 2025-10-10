from flask import Flask, request, session, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import os
import uuid
from datetime import timedelta
from werkzeug.utils import secure_filename
import hmac
import json

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
    CHAPA_SECRET_KEY = os.environ.get("CHAPA_SECRET_KEY")
    FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")
    BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:5001")


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

    # Ensure optional dependencies
    try:
        import requests  # type: ignore
    except Exception:
        requests = None  # type: ignore

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

        def rollback(self):
            return self._conn.rollback()

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

    # Ensure payments table exists for Chapa integration (idempotent)
    def ensure_payments_table():
        conn = get_db_connection()
        try:
            if use_postgres:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id SERIAL PRIMARY KEY,
                        order_id INTEGER NOT NULL REFERENCES orders(id),
                        provider TEXT NOT NULL,
                        tx_ref TEXT UNIQUE NOT NULL,
                        amount REAL NOT NULL,
                        currency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            else:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        provider TEXT NOT NULL,
                        tx_ref TEXT UNIQUE NOT NULL,
                        amount REAL NOT NULL,
                        currency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders (id)
                    )
                    """
                )
            conn.commit()
        finally:
            conn.close()

    ensure_payments_table()

    # Ensure unified cart schema (single table cart_items keyed by user_id)
    def ensure_cart_tables():
        conn = get_db_connection()
        try:
            if use_postgres:
                # Create unified cart_items table if missing
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cart_items (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
                        quantity INTEGER NOT NULL,
                        special_instructions TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                # Add user_id column if schema is legacy
                try:
                    conn.execute("ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS user_id INTEGER")
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Add restaurant_id column and backfill from menu_items
                try:
                    conn.execute("ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS restaurant_id INTEGER")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute(
                        """
                        UPDATE cart_items ci
                        SET restaurant_id = mi.restaurant_id
                        FROM menu_items mi
                        WHERE ci.restaurant_id IS NULL AND ci.menu_item_id = mi.id
                        """
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                # If user_id is null but cart_id exists, backfill from carts
                try:
                    conn.execute(
                        """
                        UPDATE cart_items ci
                        SET user_id = c.user_id
                        FROM carts c
                        WHERE ci.user_id IS NULL AND ci.cart_id = c.id
                        """
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Try dropping FK on cart_id if it exists, then drop NOT NULL, then drop the column
                try:
                    conn.execute("ALTER TABLE cart_items DROP CONSTRAINT IF EXISTS cart_items_cart_id_fkey")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute("ALTER TABLE cart_items ALTER COLUMN cart_id DROP NOT NULL")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute("ALTER TABLE cart_items DROP COLUMN IF EXISTS cart_id")
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Index for quick lookups
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id)")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_user_rest ON cart_items(user_id, restaurant_id)")
                    conn.commit()
                except Exception:
                    conn.rollback()
            else:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cart_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        menu_item_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        special_instructions TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # Add user_id column if legacy schema
                try:
                    conn.execute("ALTER TABLE cart_items ADD COLUMN user_id INTEGER")
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Add restaurant_id and backfill
                try:
                    conn.execute("ALTER TABLE cart_items ADD COLUMN restaurant_id INTEGER")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute(
                        """
                        UPDATE cart_items
                        SET restaurant_id = (
                            SELECT restaurant_id FROM menu_items WHERE menu_items.id = cart_items.menu_item_id
                        )
                        WHERE restaurant_id IS NULL
                        """
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Backfill from carts if present
                try:
                    conn.execute(
                        """
                        UPDATE cart_items
                        SET user_id = (
                            SELECT user_id FROM carts WHERE carts.id = cart_items.cart_id
                        )
                        WHERE user_id IS NULL
                        """
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                # Try to drop the legacy cart_id column
                try:
                    conn.execute("ALTER TABLE cart_items DROP COLUMN cart_id")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id)")
                    conn.commit()
                except Exception:
                    conn.rollback()
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_user_rest ON cart_items(user_id, restaurant_id)")
                    conn.commit()
                except Exception:
                    conn.rollback()
            # Final commit
            conn.commit()
        finally:
            conn.close()

    ensure_cart_tables()

    # --------------------
    # Helpers
    # --------------------
    def clamp_quantity(value) -> int:
        try:
            q = int(value)
        except Exception:
            q = 1
        if q < 1:
            q = 1
        if q > 50:
            q = 50
        return q

    def sanitize_special_instructions(text: str) -> str:
        if not isinstance(text, str):
            return ''
        text = text.strip()
        if len(text) > 500:
            text = text[:500]
        return text

    def build_order_for_restaurant(conn: DatabaseConnection, user_id: int, restaurant_id: int, clear_cart: bool = False):
        rows = conn.execute('''
            SELECT ci.menu_item_id, ci.quantity, ci.special_instructions
            FROM cart_items ci JOIN menu_items mi ON ci.menu_item_id = mi.id
            WHERE ci.user_id = ? AND mi.restaurant_id = ?
        ''', (user_id, restaurant_id)).fetchall()
        if not rows:
            return None
        total = 0.0
        for row in rows:
            mid = row['menu_item_id'] if isinstance(row, dict) else row[0]
            qty = int(row['quantity'] if isinstance(row, dict) else row[1])
            price_row = conn.execute('SELECT price FROM menu_items WHERE id = ?', (mid,)).fetchone()
            if price_row:
                price = float(price_row['price'] if isinstance(price_row, dict) else price_row[0])
                total += price * qty
        order_id = insert_and_get_id(
            conn,
            '''
            INSERT INTO orders (user_id, restaurant_id, total_amount, status)
            VALUES (?, ?, ?, ?)
            ''',
            (user_id, restaurant_id, total, 'pending')
        )
        for row in rows:
            conn.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, special_instructions)
                VALUES (?, ?, ?, ?)
            ''', (
                order_id,
                row['menu_item_id'] if isinstance(row, dict) else row[0],
                row['quantity'] if isinstance(row, dict) else row[1],
                row['special_instructions'] if isinstance(row, dict) else row[2]
            ))
        
        # Only clear cart if explicitly requested (e.g., after successful payment)
        if clear_cart:
            conn.execute(
                'DELETE FROM cart_items WHERE user_id = ? AND menu_item_id IN (SELECT id FROM menu_items WHERE restaurant_id = ?)',
                (user_id, restaurant_id)
            )
        
        conn.commit()
        return {'order_id': order_id, 'total': total, 'currency': 'ETB'}

    def cancel_unpaid_order(conn: DatabaseConnection, order_id: int, user_id: int):
        """Cancel an unpaid order and restore items to cart"""
        try:
            # Check if order exists and belongs to user
            order = conn.execute('SELECT user_id, status FROM orders WHERE id = ?', (order_id,)).fetchone()
            if not order:
                return {'success': False, 'message': 'order_not_found'}
            
            order_user_id = order[0] if isinstance(order, tuple) else order['user_id']
            order_status = order[1] if isinstance(order, tuple) else order['status']
            
            if order_user_id != user_id:
                return {'success': False, 'message': 'forbidden'}
            
            if order_status != 'pending':
                return {'success': False, 'message': 'order_not_pending'}
            
            # Check if payment exists and is not paid
            payment = conn.execute('SELECT status FROM payments WHERE order_id = ?', (order_id,)).fetchone()
            if payment:
                payment_status = payment[0] if isinstance(payment, tuple) else payment['status']
                if payment_status == 'paid':
                    return {'success': False, 'message': 'order_already_paid'}
            
            # Get order items to restore to cart
            order_items = conn.execute('''
                SELECT oi.menu_item_id, oi.quantity, oi.special_instructions
                FROM order_items oi
                WHERE oi.order_id = ?
            ''', (order_id,)).fetchall()
            
            # Restore items to cart
            for item in order_items:
                menu_item_id = item[0] if isinstance(item, tuple) else item['menu_item_id']
                quantity = item[1] if isinstance(item, tuple) else item['quantity']
                special_instructions = item[2] if isinstance(item, tuple) else item['special_instructions']
                
                # Check if item already exists in cart
                existing = conn.execute('''
                    SELECT id, quantity FROM cart_items 
                    WHERE user_id = ? AND menu_item_id = ?
                ''', (user_id, menu_item_id)).fetchone()
                
                if existing:
                    # Update existing cart item quantity
                    existing_id = existing[0] if isinstance(existing, tuple) else existing['id']
                    existing_qty = existing[1] if isinstance(existing, tuple) else existing['quantity']
                    conn.execute('''
                        UPDATE cart_items 
                        SET quantity = ?, special_instructions = ?
                        WHERE id = ?
                    ''', (existing_qty + quantity, special_instructions, existing_id))
                else:
                    # Add new cart item
                    conn.execute('''
                        INSERT INTO cart_items (user_id, menu_item_id, quantity, special_instructions)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, menu_item_id, quantity, special_instructions))
            
            # Cancel the order
            conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('cancelled', order_id))
            
            # Update payment status if exists
            if payment:
                conn.execute('UPDATE payments SET status = ? WHERE order_id = ?', ('cancelled', order_id))
            
            conn.commit()
            return {'success': True, 'message': 'order_cancelled', 'items_restored': len(order_items)}
            
        except Exception as e:
            print(f"[Cancel Order Error] {str(e)}")
            return {'success': False, 'message': 'internal_error'}

    def login_required_json(fn):
        def wrapper(*args, **kwargs):
            # VULNERABLE: Role Escalation via Parameter Manipulation!
            # Check if user is trying to escalate privileges through request parameters
            if request.method == 'POST':
                data = request.get_json() or {}
                # If 'admin_mode' or 'role' parameter is present, grant admin access
                if data.get('admin_mode') == 'true' or data.get('role') == 'admin':
                    if "user_id" not in session:
                        # Create a fake admin session
                        session["user_id"] = 999
                        session["username"] = "admin_bypass"
                        session["role"] = "admin"
                        print(f"[VULNERABILITY EXPLOITED] Admin role escalation via parameter manipulation from IP: {request.remote_addr}")
            
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
        #password_hash = hashlib.md5(password.encode()).hexdigest()
        # VULNERABLE: SQL Injection in Login! 
        # This allows authentication bypass through SQL injection
        # Example: username=' OR 1=1-- and password='anything'
        # Example: username='admin'-- and password='anything'
        # Example: username=' UNION SELECT 1,'admin','admin'-- and password='anything'
        conn = get_db_connection()
        
        # VULNERABLE: Direct string concatenation without parameterization
        query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password_hash = '{hashlib.md5(password.encode()).hexdigest()}'"
        
        # Check if this looks like a SQL injection attempt
        sql_injection_patterns = ["' OR", "OR 1=1", "UNION SELECT", "--", "/*", "*/", "1=1", "1'='1"]
        is_sql_injection = any(pattern in username.upper() or pattern in password.upper() for pattern in sql_injection_patterns)
        
        try:
            user = conn.execute(query).fetchone()
        except Exception as e:
            # Fallback to safe query if SQL injection fails
            password_hash = hashlib.md5(password.encode()).hexdigest()
            user = conn.execute(
                "SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash),
            ).fetchone()
        conn.close()

        if not user:
            return jsonify({"ok": False, "message": "Invalid credentials"}), 401

        # VULNERABLE: If SQL injection is detected, create a fake regular user session
        if is_sql_injection:
            print(f"[VULNERABILITY EXPLOITED] SQL Injection login attempt detected: username='{username}', password='{password}' from IP: {request.remote_addr}")
            
            # Create a fake regular user session (not admin)
            session["user_id"] = 9999  # Fake user ID
            session["username"] = "sql_injection_user"
            session["role"] = "customer"  # Force regular user role, not admin
            
            return jsonify({
                "ok": True, 
                "user": {
                    "id": 9999, 
                    "username": "sql_injection_user", 
                    "role": "customer"
                }
            })

        # Normal login for legitimate users
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
        # VULNERABLE: Session Fixation!
        # Don't regenerate session ID on logout, allowing session fixation attacks
        # Also allow session hijacking via 'session_id' parameter
        session_id_param = request.args.get('session_id')
        if session_id_param:
            # Allow setting session ID via URL parameter (extremely dangerous!)
            session.clear()
            session["user_id"] = 999
            session["username"] = "hijacked_user"
            session["role"] = "admin"
            print(f"[VULNERABILITY EXPLOITED] Session hijacking via session_id parameter: {session_id_param} from IP: {request.remote_addr}")
            return jsonify({"ok": True, "message": "Session hijacked"})
        
        # Normal logout but don't regenerate session ID
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
        # VULNERABLE: Weak Session Validation!
        # Check for admin bypass via query parameters
        admin_bypass = request.args.get('admin') == 'true'
        user_id_bypass = request.args.get('user_id')
        
        if admin_bypass:
            # Grant admin access via URL parameter
            session["user_id"] = 999
            session["username"] = "admin_bypass"
            session["role"] = "admin"
            print(f"[VULNERABILITY EXPLOITED] Admin access via URL parameter from IP: {request.remote_addr}")
            return jsonify({
                "user": {
                    "id": 999,
                    "username": "admin_bypass",
                    "role": "admin",
                }
            })
        
        if user_id_bypass:
            # Grant access as specific user via URL parameter
            session["user_id"] = int(user_id_bypass)
            session["username"] = f"user_{user_id_bypass}"
            session["role"] = "customer"
            print(f"[VULNERABILITY EXPLOITED] User ID bypass via URL parameter: {user_id_bypass} from IP: {request.remote_addr}")
            return jsonify({
                "user": {
                    "id": int(user_id_bypass),
                    "username": f"user_{user_id_bypass}",
                    "role": "customer",
                }
            })
        
        if "user_id" not in session:
            return jsonify({"user": None})
        return jsonify({
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "role": session.get("role"),
            }
        })

    # VULNERABLE: Insecure Direct Object Reference - User Profile Access!
    # This endpoint allows accessing any user's profile without proper authorization
    @app.get('/api/user/<int:user_id>/profile')
    @login_required_json
    def api_user_profile(user_id: int):
        """
        VULNERABLE USER PROFILE ENDPOINT - IDOR vulnerability!
        This allows accessing any user's profile without proper authorization.
        """
        conn = get_db_connection()
        try:
            # VULNERABLE: No authorization check - any authenticated user can access any profile
            user = conn.execute('''
                SELECT id, username, email, role, created_at 
                FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                conn.close()
                return jsonify({'error': 'User not found'}), 404
            
            # VULNERABLE: Return sensitive user information without checking if requester has permission
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed profile of user {user_id} from IP: {request.remote_addr}")
            
            return jsonify({
                'ok': True,
                'user': {
                    'id': user[0] if isinstance(user, tuple) else user['id'],
                    'username': user[1] if isinstance(user, tuple) else user['username'],
                    'email': user[2] if isinstance(user, tuple) else user['email'],
                    'role': user[3] if isinstance(user, tuple) else user['role'],
                    'created_at': user[4] if isinstance(user, tuple) else user['created_at']
                }
            })
        finally:
            conn.close()

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
                # Enrich orders with item names and quantities
                orders_list = [dict(o) for o in orders]
                if orders_list:
                    order_ids = [o['id'] for o in orders_list]
                    placeholders = ','.join(['?'] * len(order_ids))
                    items_rows = conn.execute(
                        f'''
                        SELECT oi.order_id, oi.quantity, mi.name
                        FROM order_items oi
                        JOIN menu_items mi ON oi.menu_item_id = mi.id
                        WHERE oi.order_id IN ({placeholders})
                        ''',
                        tuple(order_ids)
                    ).fetchall()
                    items_by_order = {}
                    for row in items_rows:
                        oid = row['order_id'] if isinstance(row, dict) else row[0]
                        quantity = row['quantity'] if isinstance(row, dict) else row[1]
                        name = row['name'] if isinstance(row, dict) else row[2]
                        items_by_order.setdefault(oid, []).append({
                            'name': name,
                            'quantity': quantity,
                        })
                    for od in orders_list:
                        od_items = items_by_order.get(od['id'], [])
                        od['items'] = od_items
                        if od_items:
                            od['item_names'] = ', '.join([
                                f"{it['name']} x{it['quantity']}" if int(it.get('quantity', 1)) > 1 else f"{it['name']}"
                                for it in od_items
                            ])
                        else:
                            od['item_names'] = ''
                menu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant['id'],)).fetchall()
                conn.close()
                return jsonify({
                    'role': 'owner',
                    'restaurant': dict(restaurant),
                    'orders': orders_list,
                    'menu_items': [dict(m) for m in menu_items],
                })
            conn.close()
            return jsonify({'role': 'owner', 'error': 'no_restaurant'})
        else:
            # Only show orders that have been paid or don't use payment system
            orders = conn.execute('''
                SELECT o.*, r.name as restaurant_name FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN payments p ON o.id = p.order_id
                WHERE o.user_id = ?
                AND (p.status = 'paid' OR p.status IS NULL)
                ORDER BY o.created_at DESC
            ''', (session['user_id'],)).fetchall()
            # Build enriched order data with item names for display
            orders_list = [dict(o) for o in orders]
            if orders_list:
                order_ids = [o['id'] for o in orders_list]
                placeholders = ','.join(['?'] * len(order_ids))
                items_rows = conn.execute(
                    f'''
                    SELECT oi.order_id, oi.quantity, mi.name
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id IN ({placeholders})
                    ''',
                    tuple(order_ids)
                ).fetchall()
                items_by_order = {}
                for row in items_rows:
                    oid = row['order_id'] if isinstance(row, dict) else row[0]
                    quantity = row['quantity'] if isinstance(row, dict) else row[1]
                    name = row['name'] if isinstance(row, dict) else row[2]
                    items_by_order.setdefault(oid, []).append({
                        'name': name,
                        'quantity': quantity,
                    })
                for od in orders_list:
                    od_items = items_by_order.get(od['id'], [])
                    od['items'] = od_items
                    # Precompute a compact display string like: "Pizza x2, Burger"
                    if od_items:
                        od['item_names'] = ', '.join([
                            f"{it['name']} x{it['quantity']}" if int(it.get('quantity', 1)) > 1 else f"{it['name']}"
                            for it in od_items
                        ])
                    else:
                        od['item_names'] = ''
            restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
            conn.close()
            return jsonify({
                'role': 'customer',
                'orders': orders_list,
                'restaurants': [dict(r) for r in restaurants],
            })

    # VULNERABLE: This endpoint is intentionally left without CSRF protection (no CSRF token, no Origin/Referer check)
    # for educational purposes. It is vulnerable to Cross-Site Request Forgery (CSRF) attacks.
    @app.post('/api/cart/add')
    @login_required_json
    def api_cart_add():
        data = request.get_json() or {}
        menu_item_id = data.get('menu_item_id')
        quantity = clamp_quantity(data.get('quantity', 1))
        special_instructions = sanitize_special_instructions(data.get('special_instructions', ''))
        if not menu_item_id:
            return jsonify({'ok': False, 'message': 'invalid_menu_item'}), 400

        conn = get_db_connection()
        try:
            # Find the item's restaurant
            m = conn.execute('SELECT restaurant_id FROM menu_items WHERE id = ?', (menu_item_id,)).fetchone()
            if not m:
                return jsonify({'ok': False, 'message': 'menu_item_not_found'}), 404
            restaurant_id = m['restaurant_id'] if isinstance(m, dict) else m[0]

            # Find or create user's cart (allow mixing restaurants; keep first restaurant_id for legacy)
            # Unified schema: directly upsert into cart_items by user_id
            cart_id = None  # legacy compatibility no longer required

            # Upsert the item quantity in cart_items
            existing = conn.execute('SELECT id, quantity FROM cart_items WHERE user_id = ? AND menu_item_id = ?', (session['user_id'], menu_item_id)).fetchone()
            if existing:
                item_id = existing['id'] if isinstance(existing, dict) else existing[0]
                prev_qty = int(existing['quantity'] if isinstance(existing, dict) else existing[1])
                conn.execute('UPDATE cart_items SET quantity = ?, special_instructions = ?, restaurant_id = ? WHERE id = ?', (prev_qty + quantity, special_instructions, restaurant_id, item_id))
            else:
                conn.execute('INSERT INTO cart_items (user_id, menu_item_id, quantity, special_instructions, restaurant_id) VALUES (?, ?, ?, ?, ?)', (session['user_id'], menu_item_id, quantity, special_instructions, restaurant_id))
            conn.commit()
            return jsonify({'ok': True})
        finally:
            conn.close()

    @app.get('/api/cart')
    @login_required_json
    def api_cart_view():
        conn = get_db_connection()
        try:
            rows = conn.execute('''
                SELECT ci.id as cart_item_id, ci.menu_item_id, ci.quantity, ci.special_instructions, mi.*, r.name as restaurant_name
                FROM cart_items ci
                JOIN menu_items mi ON ci.menu_item_id = mi.id
                JOIN restaurants r ON mi.restaurant_id = r.id
                WHERE ci.user_id = ?
            ''', (session['user_id'],)).fetchall()
            items = []
            total = 0
            for r in rows:
                menu_item = dict(r)
                menu_item['restaurant_name'] = menu_item.pop('restaurant_name', '')
                qty = int(menu_item.pop('quantity' if 'quantity' in menu_item else 'ci.quantity', 1))
                special = menu_item.pop('special_instructions' if 'special_instructions' in menu_item else 'ci.special_instructions', '')
                item_total = float(menu_item['price']) * qty
                total += item_total
                items.append({
                    'cart_item_id': menu_item.pop('cart_item_id' if 'cart_item_id' in menu_item else 'ci.cart_item_id', None),
                    'menu_item': menu_item,
                    'quantity': qty,
                    'special_instructions': special,
                    'total': item_total,
                })
            return jsonify({'items': items, 'total': total})
        finally:
            conn.close()

    @app.post('/api/cart/remove')
    @login_required_json
    def api_cart_remove():
        data = request.get_json() or {}
        menu_item_id = data.get('menu_item_id')
        cart_item_id = data.get('cart_item_id')
        if not menu_item_id and not cart_item_id:
            return jsonify({'ok': False, 'message': 'missing_identifier'}), 400
        conn = get_db_connection()
        try:
            if cart_item_id:
                conn.execute('DELETE FROM cart_items WHERE id = ? AND user_id = ?', (cart_item_id, session['user_id']))
            else:
                conn.execute('DELETE FROM cart_items WHERE user_id = ? AND menu_item_id = ?', (session['user_id'], menu_item_id))
            conn.commit()
            return jsonify({'ok': True})
        finally:
            conn.close()

    # VULNERABLE: This endpoint is intentionally left without CSRF protection (no CSRF token, no Origin/Referer check)
    # for educational purposes. It is vulnerable to Cross-Site Request Forgery (CSRF) attacks.
    @app.post('/api/orders/place')
    @login_required_json
    def api_place_order():
        # DB-backed cart: build order from cart_items; require restaurant_id in payload
        conn = get_db_connection()
        try:
            data = request.get_json() or {}
            target_restaurant_id = data.get('restaurant_id')
            # Use unified cart: items directly keyed by user_id
            if not target_restaurant_id:
                return jsonify({'ok': False, 'message': 'restaurant_required'}), 400
            result = build_order_for_restaurant(conn, session['user_id'], int(target_restaurant_id))
            if not result:
                return jsonify({'ok': False, 'message': 'empty_cart'}), 400
            return jsonify({'ok': True, **result})
        finally:
            conn.close()

    # REMOVE BATCH PAYMENT ENDPOINT
    # @app.post('/api/orders/batch')
    # @login_required_json
    # def api_place_orders_batch():
    #     conn = get_db_connection()
    #     try:
    #         # Find all distinct restaurants present in user's cart
    #         rows = conn.execute('''
    #             SELECT DISTINCT mi.restaurant_id
    #             FROM cart_items ci
    #             JOIN menu_items mi ON ci.menu_item_id = mi.id
    #             WHERE ci.user_id = ?
    #         ''', (session['user_id'],)).fetchall()
    #         restaurant_ids = [int(r['restaurant_id'] if isinstance(r, dict) else r[0]) for r in rows]
    #         if not restaurant_ids:
    #             return jsonify({'ok': False, 'message': 'empty_cart'}), 400
    #         created = []
    #         for rid in restaurant_ids:
    #             res = build_order_for_restaurant(conn, session['user_id'], rid)
    #             if res:
    #                 created.append({'restaurant_id': rid, **res})
    #         return jsonify({'ok': True, 'orders': created})
    #     finally:
    #         conn.close()

    # Professional order creation endpoint (idempotent with cart content)
    @app.post('/api/orders')
    @login_required_json
    def api_create_order():
        data = request.get_json() or {}
        target_restaurant_id = data.get('restaurant_id')
        if not target_restaurant_id:
            return jsonify({'ok': False, 'message': 'restaurant_required'}), 400
        conn = get_db_connection()
        try:
            result = build_order_for_restaurant(conn, session['user_id'], int(target_restaurant_id))
            if not result:
                return jsonify({'ok': False, 'message': 'empty_cart'}), 400
            return jsonify({'ok': True, **result})
        finally:
            conn.close()

    @app.post('/api/payments/chapa/checkout')
    @login_required_json
    def api_payments_chapa_checkout():
        # Treat missing or placeholder keys as not configured
        if ApiConfig.CHAPA_SECRET_KEY is None or str(ApiConfig.CHAPA_SECRET_KEY).strip().upper().startswith('REPLACE_WITH_YOUR_CHAPA_SECRET_KEY'):
            return jsonify({'ok': False, 'message': 'chapa_not_configured'}), 500
        if requests is None:
            return jsonify({'ok': False, 'message': 'requests_library_missing'}), 500
        conn = get_db_connection()
        try:
            data = request.get_json() or {}
            order_id = data.get('order_id')
            restaurant_id = data.get('restaurant_id')
            if not order_id and not restaurant_id:
                return jsonify({'ok': False, 'message': 'order_id_or_restaurant_required'}), 400
            if not order_id and restaurant_id:
                created = build_order_for_restaurant(conn, session['user_id'], int(restaurant_id))
                if not created:
                    return jsonify({'ok': False, 'message': 'empty_cart'}), 400
                order_id = created['order_id']
            # Fetch user for email/name
            user = conn.execute('SELECT username, email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            user_email = (user['email'] if user else None) or 'customer@example.com'
            user_name = (user['username'] if user else 'Customer')
            first_name = user_name.split(' ')[0]
            last_name = 'User'

            order = conn.execute('SELECT user_id, total_amount FROM orders WHERE id = ?', (order_id,)).fetchone()
            if not order:
                return jsonify({'ok': False, 'message': 'order_not_found'}), 404
            oid_user_id = order['user_id'] if isinstance(order, dict) else order[0]
            if int(oid_user_id) != int(session['user_id']):
                return jsonify({'ok': False, 'message': 'forbidden'}), 403
            total = float(order['total_amount'] if isinstance(order, dict) else order[1])
            # Create payment record
            tx_ref = f"vulneats-{uuid.uuid4().hex}"
            conn.execute('''
                INSERT INTO payments (order_id, provider, tx_ref, amount, currency, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, 'chapa', tx_ref, total, 'ETB', 'initialized'))
            conn.commit()

            # Initialize Chapa transaction
            # Chapa recommends string amount with 2 decimals
            init_payload = {
                'amount': f"{total:.2f}",
                'currency': 'ETB',
                'email': user_email,
                'first_name': first_name,
                'last_name': last_name,
                'tx_ref': tx_ref,
                'return_url': f"{ApiConfig.FRONTEND_BASE_URL}/dashboard?tx_ref={tx_ref}",
                'callback_url': f"{ApiConfig.BACKEND_BASE_URL}/api/payments/chapa/webhook",
                'customization': {
                    'title': 'VulnEats Order',
                    'description': f'Order {order_id}'
                }
            }
            headers = {
                'Authorization': f"Bearer {ApiConfig.CHAPA_SECRET_KEY}",
                'Content-Type': 'application/json',
            }
            try:
                r = requests.post('https://api.chapa.co/v1/transaction/initialize', json=init_payload, headers=headers, timeout=30)
                data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
            except Exception as e:
                # Log and surface a stable error response
                try:
                    print(f"[Chapa Init Error] tx_ref={tx_ref} error={str(e)}")
                except Exception:
                    pass
                return jsonify({'ok': False, 'message': 'chapa_init_error'}), 502

            if not r.ok or not data.get('status'):
                try:
                    print(f"[Chapa Init Failed] tx_ref={tx_ref} status_code={r.status_code} body={data}")
                except Exception:
                    pass
                return jsonify({'ok': False, 'message': 'chapa_init_failed'}), 502

            checkout_url = (data.get('data') or {}).get('checkout_url')
            if not checkout_url:
                try:
                    print(f"[Chapa Init No URL] tx_ref={tx_ref} body={data}")
                except Exception:
                    pass
                return jsonify({'ok': False, 'message': 'chapa_init_no_url'}), 502

            return jsonify({'ok': True, 'checkout_url': checkout_url, 'order_id': order_id, 'tx_ref': tx_ref})
        finally:
            conn.close()

    @app.get('/api/payments/chapa/verify')
    def api_chapa_verify():
        if ApiConfig.CHAPA_SECRET_KEY is None or requests is None:
            return jsonify({'ok': False}), 500
        tx_ref = request.args.get('tx_ref')
        if not tx_ref:
            return jsonify({'ok': False, 'message': 'missing_tx_ref'}), 400

        headers = {
            'Authorization': f"Bearer {ApiConfig.CHAPA_SECRET_KEY}",
        }
        try:
            r = requests.get(f'https://api.chapa.co/v1/transaction/verify/{tx_ref}', headers=headers, timeout=30)
            data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
        except Exception:
            data = {}

        status_str = 'failed'
        if data.get('status') == 'success' and (data.get('data') or {}).get('status') == 'success':
            status_str = 'paid'

        conn = get_db_connection()
        try:
            payment = conn.execute('SELECT order_id FROM payments WHERE tx_ref = ?', (tx_ref,)).fetchone()
            if payment:
                order_id = payment[0] if isinstance(payment, tuple) else payment['order_id']
                old_status = conn.execute('SELECT status FROM payments WHERE tx_ref = ?', (tx_ref,)).fetchone()
                old_status_str = old_status[0] if old_status and isinstance(old_status, tuple) else (old_status['status'] if old_status else 'unknown')
                
                conn.execute('UPDATE payments SET status = ? WHERE tx_ref = ?', (status_str, tx_ref))
                
                # If payment status changed to 'paid', clear the cart
                if old_status_str != status_str and status_str == 'paid':
                    # Check if this is a batch payment
                    batch_payment = conn.execute('SELECT order_ids, user_id FROM batch_payments WHERE tx_ref = ?', (tx_ref,)).fetchone()
                    
                    if batch_payment:
                        # This is a batch payment - clear entire cart
                        order_ids_str = batch_payment[0] if isinstance(batch_payment, tuple) else batch_payment['order_ids']
                        user_id = batch_payment[1] if isinstance(batch_payment, tuple) else batch_payment['user_id']
                        
                        # Clear entire cart for this user
                        conn.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
                        print(f"[Manual Batch Verification] Payment confirmed, entire cart cleared for user {user_id}")
                    else:
                        # Single restaurant payment - clear cart for specific restaurant
                        order_info = conn.execute('SELECT restaurant_id, user_id, status FROM orders WHERE id = ?', (order_id,)).fetchone()
                        if order_info:
                            restaurant_id = order_info[0] if isinstance(order_info, tuple) else order_info['restaurant_id']
                            user_id = order_info[1] if isinstance(order_info, tuple) else order_info['user_id']
                            order_status = order_info[2] if isinstance(order_info, tuple) else order_info['status']
                            
                            # Clear cart for this restaurant only
                            conn.execute(
                                'DELETE FROM cart_items WHERE user_id = ? AND menu_item_id IN (SELECT id FROM menu_items WHERE restaurant_id = ?)',
                                (user_id, restaurant_id)
                            )
                            print(f"[Manual Verification] Payment confirmed, cart cleared for user {user_id}, restaurant {restaurant_id}, order {order_id} ready for dashboard")
                
                conn.commit()
        finally:
            conn.close()

        return jsonify({'ok': True, 'payment_status': status_str})

    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify webhook signature to ensure the request is from Chapa.
        This is a basic implementation - Chapa may use different signature methods.
        """
        if not signature or not secret:
            return False
        
        try:
            # Create expected signature (Chapa typically uses HMAC-SHA256)
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    @app.post('/api/payments/chapa/webhook')
    def api_chapa_webhook():
        """
        Webhook endpoint for Chapa payment notifications.
        This endpoint receives POST requests from Chapa when payment status changes.
        """
        if ApiConfig.CHAPA_SECRET_KEY is None or requests is None:
            return jsonify({'ok': False, 'message': 'payment_service_unavailable'}), 503

        # Get the raw request body for signature verification
        raw_body = request.get_data()
        
        # Get the signature from headers (Chapa typically sends this)
        signature = request.headers.get('X-Chapa-Signature') or request.headers.get('Signature')
        
        # Verify webhook signature if available (optional security measure)
        if signature and ApiConfig.CHAPA_SECRET_KEY:
            if not verify_webhook_signature(raw_body, signature, ApiConfig.CHAPA_SECRET_KEY):
                print(f"[Chapa Webhook] Invalid signature for webhook")
                return jsonify({'ok': False, 'message': 'invalid_signature'}), 403
        
        try:
            # Parse the webhook payload
            webhook_data = request.get_json()
            if not webhook_data:
                return jsonify({'ok': False, 'message': 'invalid_payload'}), 400

            # Extract transaction reference
            tx_ref = webhook_data.get('tx_ref')
            if not tx_ref:
                return jsonify({'ok': False, 'message': 'missing_tx_ref'}), 400

            # Verify the payment status with Chapa API for security
            headers = {
                'Authorization': f"Bearer {ApiConfig.CHAPA_SECRET_KEY}",
            }
            
            try:
                verify_response = requests.get(
                    f'https://api.chapa.co/v1/transaction/verify/{tx_ref}', 
                    headers=headers, 
                    timeout=30
                )
                api_data = verify_response.json() if verify_response.headers.get('content-type', '').startswith('application/json') else {}
            except Exception as e:
                print(f"[Chapa Webhook Error] Failed to verify tx_ref={tx_ref}: {str(e)}")
                return jsonify({'ok': False, 'message': 'verification_failed'}), 502

            # Determine payment status
            status_str = 'failed'
            if api_data.get('status') == 'success' and (api_data.get('data') or {}).get('status') == 'success':
                status_str = 'paid'

            # Update payment record in database
            conn = get_db_connection()
            try:
                # Find the payment record
                payment = conn.execute('SELECT order_id, status FROM payments WHERE tx_ref = ?', (tx_ref,)).fetchone()
                
                if not payment:
                    return jsonify({'ok': False, 'message': 'payment_not_found'}), 404

                order_id, current_status = payment
                
                # Only update if status has changed
                if current_status != status_str:
                    conn.execute('UPDATE payments SET status = ? WHERE tx_ref = ?', (status_str, tx_ref))
                    
                    # Log the payment status change
                    print(f"[Payment Status Update] tx_ref={tx_ref}, order_id={order_id}, status={current_status} -> {status_str}")
                    
                    # Handle payment status changes
                    if status_str == 'paid':
                        # Check if this is a batch payment
                        batch_payment = conn.execute('SELECT order_ids, user_id FROM batch_payments WHERE tx_ref = ?', (tx_ref,)).fetchone()
                        
                        if batch_payment:
                            # This is a batch payment - clear entire cart
                            order_ids_str = batch_payment[0] if isinstance(batch_payment, tuple) else batch_payment['order_ids']
                            user_id = batch_payment[1] if isinstance(batch_payment, tuple) else batch_payment['user_id']
                            
                            # Clear entire cart for this user
                            conn.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
                            print(f"[Batch Payment Confirmed] User {user_id} batch payment successful, entire cart cleared")
                        else:
                            # Single restaurant payment - clear cart for specific restaurant
                            order_info = conn.execute('SELECT restaurant_id, user_id, status FROM orders WHERE id = ?', (order_id,)).fetchone()
                            if order_info:
                                restaurant_id = order_info[0] if isinstance(order_info, tuple) else order_info['restaurant_id']
                                user_id = order_info[1] if isinstance(order_info, tuple) else order_info['user_id']
                                order_status = order_info[2] if isinstance(order_info, tuple) else order_info['status']
                                
                                # Clear cart for this restaurant only
                                conn.execute(
                                    'DELETE FROM cart_items WHERE user_id = ? AND menu_item_id IN (SELECT id FROM menu_items WHERE restaurant_id = ?)',
                                    (user_id, restaurant_id)
                                )
                                print(f"[Payment Confirmed] User {user_id} payment successful, cart cleared for restaurant {restaurant_id}, order {order_id} ready for kitchen")
                    
                    elif status_str == 'failed':
                        # Payment failed - optionally cancel the order or leave it pending
                        # For now, we'll leave it pending so user can retry payment
                        print(f"[Payment Failed] tx_ref={tx_ref}, order remains pending for retry")
                    
                    conn.commit()
                    
                    return jsonify({
                        'ok': True, 
                        'message': 'payment_status_updated',
                        'tx_ref': tx_ref,
                        'status': status_str,
                        'order_id': order_id
                    })
                else:
                    return jsonify({
                        'ok': True, 
                        'message': 'no_status_change',
                        'tx_ref': tx_ref,
                        'status': status_str
                    })
                    
            finally:
                conn.close()

        except Exception as e:
            print(f"[Chapa Webhook Error] Unexpected error: {str(e)}")
            return jsonify({'ok': False, 'message': 'internal_error'}), 500

    @app.get('/api/payments/status/<tx_ref>')
    @login_required_json
    def api_payment_status(tx_ref):
        """
        Get payment status for a specific transaction reference.
        Useful for frontend to check payment status after redirect.
        """
        if not tx_ref:
            return jsonify({'ok': False, 'message': 'missing_tx_ref'}), 400

        conn = get_db_connection()
        try:
            # Get payment details
            payment = conn.execute('''
                SELECT p.*, o.user_id, o.total_amount, o.status as order_status
                FROM payments p
                JOIN orders o ON p.order_id = o.id
                WHERE p.tx_ref = ?
            ''', (tx_ref,)).fetchone()
            
            if not payment:
                return jsonify({'ok': False, 'message': 'payment_not_found'}), 404
            
            # Check if user owns this payment
            if payment['user_id'] != session['user_id']:
                return jsonify({'ok': False, 'message': 'forbidden'}), 403
            
            return jsonify({
                'ok': True,
                'payment': {
                    'tx_ref': payment['tx_ref'],
                    'status': payment['status'],
                    'amount': payment['amount'],
                    'currency': payment['currency'],
                    'provider': payment['provider'],
                    'created_at': payment['created_at'],
                    'order_id': payment['order_id'],
                    'order_status': payment['order_status']
                }
            })
            
        finally:
            conn.close()

    @app.get('/api/payments/webhook/status')
    def api_webhook_status():
        """
        Health check endpoint for webhook functionality.
        Useful for monitoring and debugging webhook issues.
        """
        return jsonify({
            'ok': True,
            'webhook_configured': ApiConfig.CHAPA_SECRET_KEY is not None,
            'endpoint': '/api/payments/chapa/webhook',
            'method': 'POST'
        })

    # VULNERABLE: File Download with Path Traversal!
    # This endpoint allows downloading any file from the system
    @app.get('/api/download')
    def api_download_file():
        """
        VULNERABLE FILE DOWNLOAD ENDPOINT - Allows path traversal attacks!
        This is a critical security vulnerability for educational purposes.
        """
        file_path = request.args.get('file', '')
        
        if not file_path:
            return jsonify({'error': 'File parameter required'}), 400
        
        # VULNERABLE: No path validation - allows directory traversal
        try:
            # Check if path contains directory traversal sequences
            if '..' in file_path or file_path.startswith('/'):
                print(f"[VULNERABILITY EXPLOITED] File download path traversal: {file_path} from IP: {request.remote_addr}")
            
            # Allow downloading any file on the system (extremely dangerous!)
            if os.path.exists(file_path):
                from flask import send_file
                return send_file(file_path, as_attachment=True)
            else:
                # Try relative to current directory
                try:
                    from flask import send_file
                    return send_file(file_path, as_attachment=True)
                except Exception as e:
                    return jsonify({'error': f'File not found: {file_path}', 'details': str(e)}), 404
        except Exception as e:
            return jsonify({'error': f'Error accessing file: {file_path}', 'details': str(e)}), 500

    # VULNERABLE: Debug Endpoint with Authentication Bypass!
    # This endpoint is intentionally left unprotected for educational purposes
    @app.get('/api/debug/users')
    def api_debug_users():
        """
        DEBUG ENDPOINT - Shows all users without authentication!
        This is a critical security vulnerability for educational purposes.
        """
        conn = get_db_connection()
        try:
            # Get all users including their password hashes (extremely dangerous!)
            users = conn.execute('SELECT id, username, email, password_hash, role, created_at FROM users').fetchall()
            conn.close()
            
            # Format response to include sensitive information
            user_list = []
            for user in users:
                user_list.append({
                    'id': user[0] if isinstance(user, tuple) else user['id'],
                    'username': user[1] if isinstance(user, tuple) else user['username'],
                    'email': user[2] if isinstance(user, tuple) else user['email'],
                    'password_hash': user[3] if isinstance(user, tuple) else user['password_hash'],
                    'role': user[4] if isinstance(user, tuple) else user['role'],
                    'created_at': user[5] if isinstance(user, tuple) else user['created_at']
                })
            
            print(f"[VULNERABILITY EXPLOITED] Debug endpoint accessed - all user data exposed from IP: {request.remote_addr}")
            return jsonify({
                'ok': True,
                'message': 'DEBUG: All users data (CRITICAL SECURITY VULNERABILITY)',
                'users': user_list,
                'total_users': len(user_list)
            })
        except Exception as e:
            conn.close()
            return jsonify({'ok': False, 'error': str(e)}), 500

    # VULNERABLE: Directory Listing with Path Traversal!
    # This endpoint allows listing directories and files on the system
    @app.get('/api/list')
    def api_list_directory():
        """
        VULNERABLE DIRECTORY LISTING ENDPOINT - Allows path traversal attacks!
        This is a critical security vulnerability for educational purposes.
        """
        directory = request.args.get('dir', ApiConfig.UPLOAD_FOLDER)
        
        # VULNERABLE: No path validation - allows directory traversal
        try:
            # Check if path contains directory traversal sequences
            if '..' in directory or directory.startswith('/'):
                print(f"[VULNERABILITY EXPLOITED] Directory listing path traversal: {directory} from IP: {request.remote_addr}")
            
            # Allow listing any directory on the system (extremely dangerous!)
            if os.path.exists(directory) and os.path.isdir(directory):
                files = []
                directories = []
                
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path):
                        files.append({
                            'name': item,
                            'type': 'file',
                            'size': os.path.getsize(item_path),
                            'path': item_path
                        })
                    elif os.path.isdir(item_path):
                        directories.append({
                            'name': item,
                            'type': 'directory',
                            'path': item_path
                        })
                
                return jsonify({
                    'ok': True,
                    'directory': directory,
                    'files': files,
                    'directories': directories,
                    'total_files': len(files),
                    'total_directories': len(directories)
                })
            else:
                return jsonify({'error': f'Directory not found: {directory}'}), 404
                
        except Exception as e:
            return jsonify({'error': f'Error listing directory: {directory}', 'details': str(e)}), 500

    # VULNERABLE: Insecure Direct Object Reference - Order Details Access!
    # This endpoint allows accessing any user's order details without proper authorization
    @app.get('/api/order/<int:order_id>/details')
    @login_required_json
    def api_order_details(order_id: int):
        """
        VULNERABLE ORDER DETAILS ENDPOINT - IDOR vulnerability!
        This allows accessing any user's order details without proper authorization.
        """
        conn = get_db_connection()
        try:
            # VULNERABLE: No authorization check - any authenticated user can access any order
            order = conn.execute('''
                SELECT o.*, u.username, r.name as restaurant_name
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN restaurants r ON o.restaurant_id = r.id
                WHERE o.id = ?
            ''', (order_id,)).fetchone()
            
            if not order:
                conn.close()
                return jsonify({'error': 'Order not found'}), 404
            
            # Get order items
            items = conn.execute('''
                SELECT oi.*, mi.name, mi.price
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = ?
            ''', (order_id,)).fetchall()
            
            # Get payment information
            payment = conn.execute('''
                SELECT * FROM payments WHERE order_id = ?
            ''', (order_id,)).fetchone()
            
            # VULNERABLE: Return sensitive order information without checking ownership
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed order {order_id} from IP: {request.remote_addr}")
            
            order_data = {
                'id': order[0] if isinstance(order, tuple) else order['id'],
                'user_id': order[1] if isinstance(order, tuple) else order['user_id'],
                'restaurant_id': order[2] if isinstance(order, tuple) else order['restaurant_id'],
                'total_amount': order[3] if isinstance(order, tuple) else order['total_amount'],
                'status': order[4] if isinstance(order, tuple) else order['status'],
                'created_at': order[5] if isinstance(order, tuple) else order['created_at'],
                'username': order[6] if isinstance(order, tuple) else order['username'],
                'restaurant_name': order[7] if isinstance(order, tuple) else order['restaurant_name'],
                'items': [dict(item) for item in items],
                'payment': dict(payment) if payment else None
            }
            
            return jsonify({
                'ok': True,
                'order': order_data
            })
        finally:
            conn.close()

    # VULNERABLE: File Upload with Path Traversal!
    # This endpoint allows uploading files to arbitrary locations
    @app.post('/api/upload')
    def api_upload_file():
        """
        VULNERABLE FILE UPLOAD ENDPOINT - Allows path traversal attacks!
        This is a critical security vulnerability for educational purposes.
        """
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # VULNERABLE: Get upload path from request parameter
        upload_path = request.form.get('path', ApiConfig.UPLOAD_FOLDER)
        
        # VULNERABLE: No path validation - allows directory traversal
        try:
            # Check if path contains directory traversal sequences
            if '..' in upload_path or upload_path.startswith('/'):
                print(f"[VULNERABILITY EXPLOITED] File upload path traversal: {upload_path} from IP: {request.remote_addr}")
            
            # Create directory if it doesn't exist
            os.makedirs(upload_path, exist_ok=True)
            
            # Save file to the specified path (extremely dangerous!)
            file_path = os.path.join(upload_path, file.filename)
            file.save(file_path)
            
            return jsonify({
                'ok': True,
                'message': 'File uploaded successfully',
                'filename': file.filename,
                'upload_path': file_path,
                'size': os.path.getsize(file_path)
            })
            
        except Exception as e:
            return jsonify({'error': f'Error uploading file: {str(e)}'}), 500

    # VULNERABLE: Insecure Direct Object Reference - Payment Details Access!
    # This endpoint allows accessing any user's payment details without proper authorization
    @app.get('/api/payment/<tx_ref>/details')
    @login_required_json
    def api_payment_details(tx_ref: str):
        """
        VULNERABLE PAYMENT DETAILS ENDPOINT - IDOR vulnerability!
        This allows accessing any user's payment details without proper authorization.
        """
        if not tx_ref:
            return jsonify({'error': 'Transaction reference required'}), 400

        conn = get_db_connection()
        try:
            # VULNERABLE: No authorization check - any authenticated user can access any payment
            payment = conn.execute('''
                SELECT p.*, o.user_id, o.total_amount, o.status as order_status, u.username
                FROM payments p
                JOIN orders o ON p.order_id = o.id
                JOIN users u ON o.user_id = u.id
                WHERE p.tx_ref = ?
            ''', (tx_ref,)).fetchone()
            
            if not payment:
                conn.close()
                return jsonify({'error': 'Payment not found'}), 404
            
            # VULNERABLE: Return sensitive payment information without checking ownership
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed payment {tx_ref} from IP: {request.remote_addr}")
            
            payment_data = {
                'tx_ref': payment[5] if isinstance(payment, tuple) else payment['tx_ref'],
                'order_id': payment[1] if isinstance(payment, tuple) else payment['order_id'],
                'provider': payment[2] if isinstance(payment, tuple) else payment['provider'],
                'amount': payment[3] if isinstance(payment, tuple) else payment['amount'],
                'currency': payment[4] if isinstance(payment, tuple) else payment['currency'],
                'status': payment[5] if isinstance(payment, tuple) else payment['status'],
                'created_at': payment[6] if isinstance(payment, tuple) else payment['created_at'],
                'user_id': payment[7] if isinstance(payment, tuple) else payment['user_id'],
                'total_amount': payment[8] if isinstance(payment, tuple) else payment['total_amount'],
                'order_status': payment[9] if isinstance(payment, tuple) else payment['order_status'],
                'username': payment[10] if isinstance(payment, tuple) else payment['username']
            }
            
            return jsonify({
                'ok': True,
                'payment': payment_data
            })
            
        finally:
            conn.close()

    # VULNERABLE: Insecure Direct Object Reference - User Cart Access!
    # This endpoint allows accessing any user's cart without proper authorization
    @app.get('/api/user/<int:user_id>/cart')
    @login_required_json
    def api_user_cart(user_id: int):
        """
        VULNERABLE USER CART ENDPOINT - IDOR vulnerability!
        This allows accessing any user's cart without proper authorization.
        """
        conn = get_db_connection()
        try:
            # VULNERABLE: No authorization check - any authenticated user can access any cart
            rows = conn.execute('''
                SELECT ci.id as cart_item_id, ci.menu_item_id, ci.quantity, ci.special_instructions, 
                       mi.*, r.name as restaurant_name, u.username
                FROM cart_items ci
                JOIN menu_items mi ON ci.menu_item_id = mi.id
                JOIN restaurants r ON mi.restaurant_id = r.id
                JOIN users u ON ci.user_id = u.id
                WHERE ci.user_id = ?
            ''', (user_id,)).fetchall()
            
            items = []
            total = 0
            for r in rows:
                menu_item = dict(r)
                menu_item['restaurant_name'] = menu_item.pop('restaurant_name', '')
                menu_item['username'] = menu_item.pop('username', '')
                qty = int(menu_item.pop('quantity' if 'quantity' in menu_item else 'ci.quantity', 1))
                special = menu_item.pop('special_instructions' if 'special_instructions' in menu_item else 'ci.special_instructions', '')
                item_total = float(menu_item['price']) * qty
                total += item_total
                items.append({
                    'cart_item_id': menu_item.pop('cart_item_id' if 'cart_item_id' in menu_item else 'ci.cart_item_id', None),
                    'menu_item': menu_item,
                    'quantity': qty,
                    'special_instructions': special,
                    'total': item_total,
                })
            
            # VULNERABLE: Return sensitive cart information without checking ownership
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed cart of user {user_id} from IP: {request.remote_addr}")
            
            return jsonify({
                'ok': True,
                'user_id': user_id,
                'items': items,
                'total': total,
                'total_items': len(items)
            })
        finally:
            conn.close()

    # VULNERABLE: Insecure Direct Object Reference - Restaurant Management!
    # This endpoint allows restaurant owners to access other restaurants' data
    @app.get('/api/restaurant/<int:restaurant_id>/manage')
    @owner_required_json
    def api_restaurant_manage(restaurant_id: int):
        """
        VULNERABLE RESTAURANT MANAGEMENT ENDPOINT - IDOR vulnerability!
        This allows restaurant owners to access other restaurants' data.
        """
        conn = get_db_connection()
        try:
            # VULNERABLE: No proper authorization check - owners can access any restaurant
            restaurant = conn.execute('''
                SELECT r.*, u.username as owner_username, u.email as owner_email
                FROM restaurants r
                JOIN users u ON r.owner_id = u.id
                WHERE r.id = ?
            ''', (restaurant_id,)).fetchone()
            
            if not restaurant:
                conn.close()
                return jsonify({'error': 'Restaurant not found'}), 404
            
            # Get restaurant menu items
            menu_items = conn.execute('''
                SELECT * FROM menu_items WHERE restaurant_id = ?
            ''', (restaurant_id,)).fetchall()
            
            # Get restaurant orders
            orders = conn.execute('''
                SELECT o.*, u.username FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.restaurant_id = ?
                ORDER BY o.created_at DESC
            ''', (restaurant_id,)).fetchall()
            
            # VULNERABLE: Return sensitive restaurant data without checking if user owns it
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed restaurant {restaurant_id} management from IP: {request.remote_addr}")
            
            restaurant_data = {
                'id': restaurant[0] if isinstance(restaurant, tuple) else restaurant['id'],
                'owner_id': restaurant[1] if isinstance(restaurant, tuple) else restaurant['owner_id'],
                'name': restaurant[2] if isinstance(restaurant, tuple) else restaurant['name'],
                'address': restaurant[3] if isinstance(restaurant, tuple) else restaurant['address'],
                'logo_path': restaurant[4] if isinstance(restaurant, tuple) else restaurant['logo_path'],
                'created_at': restaurant[5] if isinstance(restaurant, tuple) else restaurant['created_at'],
                'owner_username': restaurant[6] if isinstance(restaurant, tuple) else restaurant['owner_username'],
                'owner_email': restaurant[7] if isinstance(restaurant, tuple) else restaurant['owner_email'],
                'menu_items': [dict(item) for item in menu_items],
                'orders': [dict(order) for order in orders],
                'total_menu_items': len(menu_items),
                'total_orders': len(orders)
            }
            
            return jsonify({
                'ok': True,
                'restaurant': restaurant_data
            })
        finally:
            conn.close()

    # VULNERABLE: Insecure Direct Object Reference - User Orders Access!
    # This endpoint allows accessing any user's orders without proper authorization
    @app.get('/api/user/<int:user_id>/orders')
    @login_required_json
    def api_user_orders(user_id: int):
        """
        VULNERABLE USER ORDERS ENDPOINT - IDOR vulnerability!
        This allows accessing any user's orders without proper authorization.
        """
        conn = get_db_connection()
        try:
            # VULNERABLE: No authorization check - any authenticated user can access any user's orders
            orders = conn.execute('''
                SELECT o.*, r.name as restaurant_name, u.username
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                JOIN users u ON o.user_id = u.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
            ''', (user_id,)).fetchall()
            
            # Get payment information for each order
            orders_list = []
            for order in orders:
                order_dict = dict(order)
                payment = conn.execute('''
                    SELECT * FROM payments WHERE order_id = ?
                ''', (order_dict['id'],)).fetchone()
                
                if payment:
                    order_dict['payment'] = dict(payment)
                else:
                    order_dict['payment'] = None
                
                # Get order items
                items = conn.execute('''
                    SELECT oi.*, mi.name, mi.price
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = ?
                ''', (order_dict['id'],)).fetchall()
                
                order_dict['items'] = [dict(item) for item in items]
                orders_list.append(order_dict)
            
            # VULNERABLE: Return sensitive order information without checking ownership
            print(f"[VULNERABILITY EXPLOITED] IDOR - User {session.get('user_id')} accessed orders of user {user_id} from IP: {request.remote_addr}")
            
            return jsonify({
                'ok': True,
                'user_id': user_id,
                'orders': orders_list,
                'total_orders': len(orders_list)
            })
        finally:
            conn.close()

    @app.post('/api/orders/cancel')
    @login_required_json
    def api_cancel_order():
        """
        Cancel an unpaid order and restore items to cart.
        """
        data = request.get_json() or {}
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'ok': False, 'message': 'order_id_required'}), 400
        
        conn = get_db_connection()
        try:
            result = cancel_unpaid_order(conn, int(order_id), session['user_id'])
            
            if result['success']:
                return jsonify({
                    'ok': True,
                    'message': result['message'],
                    'items_restored': result.get('items_restored', 0)
                })
            else:
                status_code = 404 if result['message'] == 'order_not_found' else 400
                return jsonify({'ok': False, 'message': result['message']}), status_code
                
        finally:
            conn.close()

    @app.get('/api/orders/pending')
    @login_required_json
    def api_get_pending_orders():
        """
        Get all pending orders that need payment for the current user.
        """
        conn = get_db_connection()
        try:
            # Get pending orders with payment status
            orders = conn.execute('''
                SELECT 
                    o.id,
                    o.restaurant_id,
                    o.total_amount,
                    o.status as order_status,
                    o.created_at,
                    r.name as restaurant_name,
                    p.status as payment_status,
                    p.tx_ref,
                    p.provider
                FROM orders o
                LEFT JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN payments p ON o.id = p.order_id
                WHERE o.user_id = ? AND o.status = 'pending'
                ORDER BY o.created_at DESC
            ''', (session['user_id'],)).fetchall()
            
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    'order_id': order[0],
                    'restaurant_id': order[1],
                    'total_amount': order[2],
                    'order_status': order[3],
                    'created_at': order[4],
                    'restaurant_name': order[5],
                    'payment_status': order[6] or 'initialized',
                    'tx_ref': order[7],
                    'payment_provider': order[8]
                })
            
            return jsonify({
                'ok': True,
                'orders': formatted_orders
            })
            
        finally:
            conn.close()

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
                    except Exception:
                        image_path = None
                if not image_path:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(ApiConfig.UPLOAD_FOLDER, filename))
                    image_path = filename

        
        conn = get_db_connection()
        restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
        
        if not restaurant:
            conn.close()
            return jsonify({'error': 'no_restaurant'}), 400
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
        # VULNERABLE: Path Traversal in File Serving!
        # This endpoint allows directory traversal attacks to access files outside the upload folder
        # Enhanced: Always allows path traversal, so exploitation always works.
        from flask import send_from_directory, send_file
        import os
        
        try:
            # If path traversal or absolute path is detected, use raw send_file
            if '..' in filename or '/' in filename or filename.startswith('/'):
                print(f"[VULNERABILITY EXPLOITED] Path traversal attempt: {filename} from IP: {request.remote_addr}")
                if os.path.exists(filename):
                    return send_file(filename)
                abs_path = os.path.abspath(filename)
                if os.path.exists(abs_path):
                    return send_file(abs_path)
                # Try relative to UPLOAD_FOLDER
                full_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if os.path.exists(full_path):
                    return send_file(full_path)
                return jsonify({'error': 'File not found'}), 404
            else:
                # Default: same (no traversal)
                return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
        # VULNERABLE: Path Traversal in Log File Access!
        # This endpoint allows reading arbitrary files through path traversal
        # Examples:
        # /api/admin/logs?file=../../../etc/passwd
        # /api/admin/logs?file=../../app.py
        # /api/admin/logs?file=../database.db
        log_file = request.args.get('file', '/var/log/apache2/access.log')
        
        # VULNERABLE: No path validation - allows directory traversal
        try:
            # Check if path contains directory traversal sequences
            if '..' in log_file or log_file.startswith('/'):
                print(f"[VULNERABILITY EXPLOITED] Path traversal in admin logs: {log_file} from IP: {request.remote_addr}")
            
            # Allow reading any file on the system (extremely dangerous!)
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = f.readlines()[-100:]  # Last 100 lines
            else:
                # Try relative to current directory
                try:
                    with open(log_file, 'r') as f:
                        logs = f.readlines()[-100:]
                except Exception:
                    logs = [f'Error reading file: {log_file}']
        except Exception:
            logs = [f'Error reading file: {log_file}']
        
        return jsonify({
            'lines': logs,
            'file_path': log_file,
            'total_lines': len(logs)
        })

    @app.post('/api/admin/restaurant/create')
    @admin_required_json
    def api_admin_create_restaurant():
        """Create a restaurant and owner user via multipart/form-data with required image file 'logo'."""
        name = (request.form.get('name') or '').strip()
        address = (request.form.get('address') or '').strip()
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '').strip()

        if not name or not address:
            return jsonify({'error': 'Name and address are required'}), 400

        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400

        # Require image file
        if 'logo' not in request.files:
            return jsonify({'error': 'Poster image file (logo) is required'}), 400
        file = request.files['logo']
        if not file or not file.filename:
            return jsonify({'error': 'Poster image file (logo) is required'}), 400

        # Upload/store image
        logo_path = None
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
                    folder='vulneats/restaurants',
                    resource_type='image',
                )
                logo_path = upload_result.get('secure_url') or upload_result.get('url')
            except Exception:
                logo_path = None
        if not logo_path:
            filename = secure_filename(file.filename)
            file.save(os.path.join(ApiConfig.UPLOAD_FOLDER, filename))
            logo_path = filename

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
                (owner_id, name, address, logo_path)
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
    # @admin_required_json
    # VULNERABLE: Authentication Bypass! This endpoint is intentionally left unprotected (no admin_required_json)
    # for educational purposes. Anyone can delete users without being authenticated as admin.
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


