from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import sqlite3
import hashlib
import os
import re
from werkzeug.utils import secure_filename
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Database connection function
def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Authentication decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = get_db_connection()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if user['role'] != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def owner_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = get_db_connection()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if user['role'] not in ['admin', 'owner']:
            flash('Access denied. Restaurant owner privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # VULNERABLE: MD5 password hashing
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                          (username, password_hash)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # VULNERABLE: MD5 password hashing
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                       (username, email, password_hash, 'customer'))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user['role'] == 'admin':
        # Admin dashboard
        restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
        orders = conn.execute('SELECT o.*, u.username, r.name as restaurant_name FROM orders o JOIN users u ON o.user_id = u.id JOIN restaurants r ON o.restaurant_id = r.id ORDER BY o.created_at DESC').fetchall()
        conn.close()
        return render_template('admin_dashboard.html', restaurants=restaurants, orders=orders)
    
    elif user['role'] == 'owner':
        # Restaurant owner dashboard
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
            return render_template('owner_dashboard.html', restaurant=restaurant, orders=orders, menu_items=menu_items)
        else:
            conn.close()
            flash('No restaurant found for this account', 'error')
            return redirect(url_for('index'))
    
    else:
        # Customer dashboard
        orders = conn.execute('''
            SELECT o.*, r.name as restaurant_name FROM orders o 
            JOIN restaurants r ON o.restaurant_id = r.id 
            WHERE o.user_id = ? 
            ORDER BY o.created_at DESC
        ''', (session['user_id'],)).fetchall()
        restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
        conn.close()
        return render_template('customer_dashboard.html', orders=orders, restaurants=restaurants)

@app.route('/restaurants')
def restaurants():
    conn = get_db_connection()
    restaurants = conn.execute('SELECT * FROM restaurants').fetchall()
    conn.close()
    return render_template('restaurants.html', restaurants=restaurants)

@app.route('/restaurant/<int:restaurant_id>')
def restaurant_menu(restaurant_id):
    conn = get_db_connection()
    restaurant = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
    menu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant_id,)).fetchall()
    conn.close()
    return render_template('restaurant_menu.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    # VULNERABLE: SQL Injection in search
    conn = get_db_connection()
    # This is intentionally vulnerable - concatenating user input directly into SQL
    sql = f"SELECT * FROM menu_items WHERE name LIKE '%{query}%' OR description LIKE '%{query}%'"
    menu_items = conn.execute(sql).fetchall()
    conn.close()
    
    return render_template('search_results.html', menu_items=menu_items, query=query)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    menu_item_id = request.form.get('menu_item_id')
    quantity = request.form.get('quantity', 1)
    special_instructions = request.form.get('special_instructions', '')
    
    # VULNERABLE: Stored XSS - storing user input without sanitization
    if 'cart' not in session:
        session['cart'] = []
    
    session['cart'].append({
        'menu_item_id': menu_item_id,
        'quantity': quantity,
        'special_instructions': special_instructions  # VULNERABLE: XSS stored here
    })
    
    flash('Item added to cart!', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/cart')
@login_required
def view_cart():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'info')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cart_items = []
    total = 0
    
    for item in session['cart']:
        menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item['menu_item_id'],)).fetchone()
        if menu_item:
            item_total = menu_item['price'] * int(item['quantity'])
            total += item_total
            cart_items.append({
                'menu_item': menu_item,
                'quantity': item['quantity'],
                'special_instructions': item['special_instructions'],
                'total': item_total
            })
    
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('dashboard'))
    
    restaurant_id = request.form.get('restaurant_id')
    
    conn = get_db_connection()
    
    # Calculate total
    total = 0
    for item in session['cart']:
        menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item['menu_item_id'],)).fetchone()
        if menu_item:
            total += menu_item['price'] * int(item['quantity'])
    
    # Create order
    cursor = conn.execute('''
        INSERT INTO orders (user_id, restaurant_id, total_amount, status)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], restaurant_id, total, 'pending'))
    
    order_id = cursor.lastrowid
    
    # Add order items
    for item in session['cart']:
        conn.execute('''
            INSERT INTO order_items (order_id, menu_item_id, quantity, special_instructions)
            VALUES (?, ?, ?, ?)
        ''', (order_id, item['menu_item_id'], item['quantity'], item['special_instructions']))
    
    conn.commit()
    conn.close()
    
    # Clear cart
    session.pop('cart', None)
    
    flash('Order placed successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update_order_status', methods=['POST'])
@owner_required
def update_order_status():
    order_id = request.form.get('order_id')
    status = request.form.get('status')
    
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    
    flash('Order status updated!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_menu_item', methods=['GET', 'POST'])
@owner_required
def add_menu_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        
        # Get restaurant for current owner
        conn = get_db_connection()
        restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
        
        if restaurant:
            # Handle file upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    # VULNERABLE: Insecure file upload - no proper validation
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                    image_path = filename
            
            conn.execute('''
                INSERT INTO menu_items (restaurant_id, name, description, price, image_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (restaurant['id'], name, description, price, image_path))
            conn.commit()
            flash('Menu item added successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        conn.close()
    
    return render_template('add_menu_item.html')

@app.route('/delete_menu_item/<int:item_id>', methods=['POST'])
@owner_required
def delete_menu_item(item_id):
    # VULNERABLE: No CSRF protection
    conn = get_db_connection()
    restaurant = conn.execute('SELECT * FROM restaurants WHERE owner_id = ?', (session['user_id'],)).fetchone()
    
    if restaurant:
        conn.execute('DELETE FROM menu_items WHERE id = ? AND restaurant_id = ?', (item_id, restaurant['id']))
        conn.commit()
        flash('Menu item deleted successfully!', 'success')
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # VULNERABLE: Directory traversal possible
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/logs')
@admin_required
def admin_logs():
    # VULNERABLE: Command injection possible
    log_file = request.args.get('file', '/var/log/apache2/access.log')
    try:
        with open(log_file, 'r') as f:
            logs = f.readlines()[-100:]  # Last 100 lines
    except:
        logs = ['Error reading log file']
    
    return render_template('admin_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
