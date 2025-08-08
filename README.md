# VulnEats - Online Food Ordering System (Cybersecurity Lab)

A deliberately vulnerable food ordering platform designed for cybersecurity education and ethical hacking practice.

## 🎯 Project Overview

VulnEats is a web application that simulates an online food ordering system with intentionally introduced security vulnerabilities. This project serves as a hands-on learning environment for understanding common web application security flaws and practicing ethical hacking techniques.

## 🧩 Core Features

### Customer Side
- User registration and login (JWT/session-based authentication)
- Browse restaurants and menus
- Search dishes by name/category
- Add items to cart and place orders
- Simulated payment processing
- View order history

### Restaurant Admin Side
- Restaurant owner login
- Add/update/delete menu items
- Upload dish images
- View and manage customer orders
- Update order status (Pending, Cooking, Delivered)

### System Admin
- Manage restaurant accounts
- View all system orders
- Access system logs
- User management

## 🗂 Deliberate Vulnerabilities

| Vulnerability | Location | Example Exploit | Security Fix |
|---------------|----------|-----------------|--------------|
| **SQL Injection** | Menu search box | `pizza' OR '1'='1` → dump all menu items | Parameterized queries |
| **Stored XSS** | Dish "special instructions" field | `<script>stealCookies()</script>` | Input sanitization + output encoding |
| **Reflected XSS** | Search results page | Inject JS via URL query string | Escape output in HTML |
| **CSRF** | Add/Delete menu item | Malicious form forces admin to delete menu item | CSRF tokens |
| **Insecure File Upload** | Restaurant logo upload | Upload `.php` web shell | File type validation + server-side MIME check |
| **Directory Traversal** | Dish image request | `../config.env` to access secrets | Path sanitization |
| **Weak Password Storage** | Users' passwords in MD5 | Crack with john | Use bcrypt/Argon2 |
| **No Rate Limiting** | Login page | Brute force with Hydra | Implement rate limiting |
| **Command Injection** | Admin log viewer | `; cat /etc/passwd` | Input validation and sanitization |

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker and Docker Compose (optional)

### Option 1: Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Vuln_FoodOrder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python init_db.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:5000`

### Option 2: Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Open your browser and go to `http://localhost:5000`

## 🔑 Default Credentials

| Role | Username | Password |
|------|----------|----------|
| **Admin** | `admin` | `admin123` |
| **Restaurant Owner** | `restaurant1` | `password123` |
| **Customer** | `customer1` | `password123` |

## 🛠 Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Deployment**: Docker + Docker Compose

## 🧪 Testing Tools

### Recommended Security Testing Tools
- **OWASP ZAP**: Web application security scanner
- **Burp Suite**: Web application security testing platform
- **sqlmap**: Automated SQL injection and database takeover tool
- **Nikto**: Web server scanner
- **Hydra**: Password brute force tool
- **John the Ripper**: Password cracking tool

### Example Exploits

#### SQL Injection
```bash
# Search for: pizza' OR '1'='1
# This will return all menu items instead of just pizza
```

#### XSS (Cross-Site Scripting)
```html
<!-- In special instructions field: -->
<script>alert('XSS')</script>
<img src="x" onerror="alert('XSS')">
```

#### CSRF (Cross-Site Request Forgery)
```html
<!-- Create a malicious form that deletes menu items -->
<form action="http://localhost:5000/delete_menu_item/1" method="POST">
  <input type="submit" value="Click for free pizza!">
</form>
```

#### File Upload Exploit
```bash
# Upload a PHP web shell disguised as an image
# Create file: shell.php.jpg with PHP code inside
```

## 📁 Project Structure

```
Vuln_FoodOrder/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── init_db.py             # Database initialization
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── restaurants.html
│   ├── restaurant_menu.html
│   ├── search_results.html
│   ├── cart.html
│   ├── customer_dashboard.html
│   ├── owner_dashboard.html
│   ├── admin_dashboard.html
│   ├── add_menu_item.html
│   ├── admin_users.html
│   └── admin_logs.html
└── uploads/              # File upload directory
```

## ⚠️ Security Disclaimer

**IMPORTANT**: This application is designed for educational purposes only. It contains deliberate security vulnerabilities and should NEVER be deployed in a production environment or exposed to the internet.

### Educational Use Only
- This application is intended for cybersecurity education
- All vulnerabilities are intentionally introduced for learning purposes
- Use only in controlled, isolated environments
- Do not use for any malicious purposes

## 🎓 Learning Objectives

By working with this application, you will learn:

1. **Common Web Vulnerabilities**: Understanding how real-world security flaws work
2. **Exploitation Techniques**: Hands-on practice with ethical hacking tools
3. **Security Testing**: How to identify and verify vulnerabilities
4. **Defense Strategies**: How to fix and prevent security issues
5. **Security Mindset**: Developing a security-conscious approach to development

## 🔧 Customization

### Adding New Vulnerabilities
1. Modify the relevant route in `app.py`
2. Update the corresponding template
3. Document the vulnerability in this README

### Hardening the Application
1. Implement proper input validation
2. Use parameterized queries
3. Add CSRF protection
4. Implement proper file upload validation
5. Use secure password hashing (bcrypt/Argon2)
6. Add rate limiting
7. Implement proper session management

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Flask Security Documentation](https://flask-security.readthedocs.io/)
- [Web Application Security Testing](https://portswigger.net/web-security)

## 🤝 Contributing

This is an educational project. Contributions that improve the learning experience are welcome:

1. Add new vulnerabilities for learning
2. Improve documentation
3. Add more realistic scenarios
4. Create additional testing tools

## 📄 License

This project is for educational purposes only. Use responsibly and ethically.

---

**Remember**: Always practice ethical hacking and only test systems you own or have explicit permission to test.
