from flask import Flask, request, session, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import os
import uuid
from datetime import timedelta
from werkzeug.utils import secure_filename
import subprocess
from io import BytesIO

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
    # INTENTIONAL MISCONFIG: Insecure session cookie and permissive CORS
    app.config.update({
        'SESSION_COOKIE_SECURE': False,
        'SESSION_COOKIE_HTTPONLY': False,
        'SESSION_COOKIE_SAMESITE': None,
    })
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

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

    def build_order_for_restaurant(conn: DatabaseConnection, user_id: int, restaurant_id: int):
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
        conn.execute(
            'DELETE FROM cart_items WHERE user_id = ? AND menu_item_id IN (SELECT id FROM menu_items WHERE restaurant_id = ?)',
            (user_id, restaurant_id)
        )
        conn.commit()
        return {'order_id': order_id, 'total': total, 'currency': 'ETB'}

    def login_required_json(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "auth_required"}), 401
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    def admin_required_json(fn):
        def wrapper(*args, **kwargs):
            # INTENTIONAL VULNERABILITY: Authorization bypass via header or query parameter
            # If X-Admin-Bypass header or ?admin=1 is present, skip all checks
            try:
                bypass_hdr = str(request.headers.get('X-Admin-Bypass', '')).lower()
                bypass_qs = str(request.args.get('admin', '') or request.args.get('bypass', '')).lower()
                if bypass_hdr in ('1', 'true', 'yes', 'on') or bypass_qs in ('1', 'true', 'yes', 'on'):
                    return fn(*args, **kwargs)
            except Exception:
                pass

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
            # INTENTIONAL VULNERABILITY: Owner bypass via header or query parameter
            try:
                bypass_hdr = str(request.headers.get('X-Owner-Bypass', '')).lower()
                bypass_qs = str(request.args.get('owner', '') or request.args.get('bypass', '')).lower()
                if bypass_hdr in ('1', 'true', 'yes', 'on') or bypass_qs in ('1', 'true', 'yes', 'on'):
                    return fn(*args, **kwargs)
            except Exception:
                pass

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

    # -------------------------------------
    # INTENTIONAL SSRF Vulnerability (Educational)
    # -------------------------------------
    @app.get('/api/ssrf')
    def api_ssrf_fetch():
        """Fetches arbitrary URLs from the server side without validation (SSRF).

        WARNING: This endpoint is intentionally vulnerable and should NOT be used in production.
        It allows requesting internal resources (e.g., 127.0.0.1, metadata services) and ignores TLS verification.
        """
        if requests is None:
            return jsonify({'ok': False, 'message': 'requests_library_missing'}), 500
        url = request.args.get('url', '').strip()
        if not url:
            return jsonify({'ok': False, 'message': 'missing_url'}), 400
        method = (request.args.get('method') or 'GET').upper()
        timeout_sec = 10
        try:
            if method == 'POST':
                data = request.args.get('data')
                r = requests.post(url, data=data, timeout=timeout_sec, verify=False, allow_redirects=True)
            else:
                r = requests.get(url, timeout=timeout_sec, verify=False, allow_redirects=True)
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 502

        # Try to pass through JSON directly; otherwise wrap into a JSON envelope
        content_type = r.headers.get('content-type', '')
        preview = None
        body_json = None
        if content_type.startswith('application/json'):
            try:
                body_json = r.json()
            except Exception:
                preview = r.text[:4000]
        else:
            preview = r.text[:4000]

        return jsonify({
            'ok': True,
            'status_code': r.status_code,
            'headers': dict(r.headers),
            'url': r.url,
            'body': body_json if body_json is not None else preview,
            'content_type': content_type,
        })

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
            orders = conn.execute('''
                SELECT o.*, r.name as restaurant_name FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                WHERE o.user_id = ?
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

    @app.post('/api/orders/batch')
    @login_required_json
    def api_place_orders_batch():
        conn = get_db_connection()
        try:
            # Find all distinct restaurants present in user's cart
            rows = conn.execute('''
                SELECT DISTINCT mi.restaurant_id
                FROM cart_items ci
                JOIN menu_items mi ON ci.menu_item_id = mi.id
                WHERE ci.user_id = ?
            ''', (session['user_id'],)).fetchall()
            restaurant_ids = [int(r['restaurant_id'] if isinstance(r, dict) else r[0]) for r in rows]
            if not restaurant_ids:
                return jsonify({'ok': False, 'message': 'empty_cart'}), 400
            created = []
            for rid in restaurant_ids:
                res = build_order_for_restaurant(conn, session['user_id'], rid)
                if res:
                    created.append({'restaurant_id': rid, **res})
            return jsonify({'ok': True, 'orders': created})
        finally:
            conn.close()

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
                'callback_url': f"{ApiConfig.BACKEND_BASE_URL}/api/payments/chapa/verify?tx_ref={tx_ref}",
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

    @app.post('/api/payments/chapa/checkout/batch')
    @login_required_json
    def api_payments_chapa_checkout_batch():
        # Ensure keys and requests lib
        if ApiConfig.CHAPA_SECRET_KEY is None:
            return jsonify({'ok': False, 'message': 'chapa_not_configured'}), 500
        try:
            import requests as _rq  # type: ignore
        except Exception:
            return jsonify({'ok': False, 'message': 'requests_library_missing'}), 500

        conn = get_db_connection()
        try:
            # Collect restaurant IDs from cart
            rid_rows = conn.execute('''
                SELECT DISTINCT mi.restaurant_id
                FROM cart_items ci
                JOIN menu_items mi ON ci.menu_item_id = mi.id
                WHERE ci.user_id = ?
            ''', (session['user_id'],)).fetchall()
            restaurant_ids = [int(r['restaurant_id'] if isinstance(r, dict) else r[0]) for r in rid_rows]
            if not restaurant_ids:
                return jsonify({'ok': False, 'message': 'empty_cart'}), 400

            # Fetch user for email/name
            user = conn.execute('SELECT username, email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            user_email = (user['email'] if user else None) or 'customer@example.com'
            user_name = (user['username'] if user else 'Customer')
            first_name = user_name.split(' ')[0]
            last_name = 'User'

            headers = {
                'Authorization': f"Bearer {ApiConfig.CHAPA_SECRET_KEY}",
                'Content-Type': 'application/json',
            }

            payments = []
            failures = []
            for rid in restaurant_ids:
                created = build_order_for_restaurant(conn, session['user_id'], rid)
                if not created:
                    continue
                order_id = created['order_id']
                total = float(created['total'])
                tx_ref = f"vulneats-{uuid.uuid4().hex}"
                conn.execute('''
                    INSERT INTO payments (order_id, provider, tx_ref, amount, currency, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, 'chapa', tx_ref, total, 'ETB', 'initialized'))
            conn.commit()

            init_payload = {
                'amount': f"{total:.2f}",
                'currency': 'ETB',
                'email': user_email,
                'first_name': first_name,
                'last_name': last_name,
                'tx_ref': tx_ref,
                'return_url': f"{ApiConfig.FRONTEND_BASE_URL}/dashboard?tx_ref={tx_ref}",
                'callback_url': f"{ApiConfig.BACKEND_BASE_URL}/api/payments/chapa/verify?tx_ref={tx_ref}",
                'customization': {
                    'title': 'VulnEats Order',
                    'description': f'Order {order_id}'
                }
            }
            try:
                r = _rq.post('https://api.chapa.co/v1/transaction/initialize', json=init_payload, headers=headers, timeout=30)
                data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
                checkout_url = (data.get('data') or {}).get('checkout_url') if r.ok else None
                if checkout_url:
                    payments.append({'order_id': order_id, 'tx_ref': tx_ref, 'checkout_url': checkout_url})
                else:
                    failures.append({'order_id': order_id, 'tx_ref': tx_ref})
            except Exception:
                failures.append({'order_id': order_id, 'tx_ref': tx_ref})

            return jsonify({'ok': True, 'payments': payments, 'failed': failures})
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
                conn.execute('UPDATE payments SET status = ? WHERE tx_ref = ?', (status_str, tx_ref))
                # If paid, keep order as pending for kitchen; otherwise, leave as is.
                conn.commit()
        finally:
            conn.close()

        return jsonify({'ok': True, 'payment_status': status_str})

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

    # INTENTIONAL MISCONFIG/LEAK: Expose environment and secrets to admins (and bypassable via ?admin=1)
    @app.get('/api/admin/config')
    @admin_required_json
    def api_admin_config_leak():
        return jsonify({
            'env': dict(os.environ),
            'api_config': {
                'DATABASE_PATH': ApiConfig.DATABASE_PATH,
                'DATABASE_URL': ApiConfig.DATABASE_URL,
                'SECRET_KEY': ApiConfig.SECRET_KEY,
                'UPLOAD_FOLDER': ApiConfig.UPLOAD_FOLDER,
                'CHAPA_SECRET_KEY': ApiConfig.CHAPA_SECRET_KEY,
                'FRONTEND_BASE_URL': ApiConfig.FRONTEND_BASE_URL,
                'BACKEND_BASE_URL': ApiConfig.BACKEND_BASE_URL,
            }
        })

    # INTENTIONAL RCE: Execute arbitrary shell commands (Educational only!)
    @app.post('/api/admin/exec')
    @admin_required_json
    def api_admin_exec():
        payload = request.get_json(silent=True) or {}
        cmd = (payload.get('cmd')
               or request.form.get('cmd')
               or request.args.get('cmd')
               or '').strip()
        if not cmd:
            return jsonify({'ok': False, 'message': 'missing_cmd'}), 400
        try:
            # Shell=True on user input is unsafe; added intentionally. Short timeout to avoid hanging.
            completed = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=8,
            )
            return jsonify({
                'ok': True,
                'exit_code': completed.returncode,
                'stdout': completed.stdout[-4000:],
                'stderr': completed.stderr[-4000:],
            })
        except subprocess.TimeoutExpired as e:
            return jsonify({'ok': False, 'message': 'timeout', 'partial_output': (e.stdout or '')[-2000:]}), 504
        except Exception as e:
            return jsonify({'ok': False, 'message': str(e)}), 500

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

    # -------------------------------------
    # INTENTIONAL XXE Vulnerability (Educational)
    # -------------------------------------
    @app.post('/api/xxe')
    def api_xxe():
        """Parses XML unsafely and returns some fields.

        Accepts XML via raw body or 'xml' form field.
        XXE payloads can read files or hit local services.
        """
        try:
            data = request.get_data(cache=False) or b''
            if not data:
                xml = request.form.get('xml', '')
                data = xml.encode()
            # Use lxml for entity expansion if installed
            try:
                from lxml import etree  # type: ignore
                parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False, huge_tree=True)
                root = etree.fromstring(data, parser)
                # Return tag names and text preview
                out = []
                for el in root.iter():
                    txt = (el.text or '')
                    out.append({'tag': el.tag, 'text': txt[:200]})
                return jsonify({'ok': True, 'engine': 'lxml', 'elements': out})
            except Exception:
                # Fallback: built-in xml parser with entity resolution via DTD (unsafe behaviors depend on runtime)
                import xml.etree.ElementTree as ET  # type: ignore
                parser = ET.XMLParser()
                root = ET.fromstring(data, parser=parser)
                out = []
                for el in root.iter():
                    txt = (el.text or '')
                    out.append({'tag': el.tag, 'text': txt[:200]})
                return jsonify({'ok': True, 'engine': 'xml.etree', 'elements': out})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)


