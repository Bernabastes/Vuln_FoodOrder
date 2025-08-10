# VulnEats Setup Complete! 🎉

## ✅ Application Status

The VulnEats food ordering system has been successfully deployed and is running on:
- **URL**: http://localhost:5000
- **Status**: ✅ Running
- **Database**: ✅ Initialized with sample data

## 🚀 Quick Access

### Default User Accounts

| Role | Username | Password | Access Level |
|------|----------|----------|--------------|
| **System Admin** | `admin` | `admin123` | Full system access |
| **Restaurant Owner** | `restaurant1` | `password123` | Manage Pizza Palace |
| **Restaurant Owner** | `restaurant2` | `password123` | Manage Burger House |
| **Customer** | `customer1` | `password123` | Order food |
| **Customer** | `customer2` | `password123` | Order food |
| **Customer** | `customer3` | `password123` | Order food |

## 🧪 Testing the Vulnerabilities

### 1. SQL Injection Test
```
URL: http://localhost:5000/search?q=pizza' OR '1'='1
Expected: All menu items returned instead of just pizza
```

### 2. XSS Test
```
1. Login as customer1
2. Add item to cart with special instructions: <script>alert('XSS')</script>
3. View cart to see stored XSS
```

### 3. CSRF Test
```
1. Login as restaurant1
2. Create malicious HTML file with form targeting delete_menu_item
3. Open file while logged in
```

### 4. File Upload Test
```
1. Login as restaurant1
2. Add menu item with malicious file upload
3. Access uploaded file to test code execution
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
├── README.md             # Main documentation
├── SECURITY_TESTING_GUIDE.md  # Detailed testing guide
├── SETUP_COMPLETE.md     # This file
├── templates/            # HTML templates (13 files)
├── uploads/              # File upload directory
└── vulneats.db          # SQLite database
```

## 🛠 Available Features

### Customer Features
- ✅ User registration and login
- ✅ Browse restaurants and menus
- ✅ Search menu items (vulnerable to SQL injection)
- ✅ Add items to cart with special instructions (vulnerable to XSS)
- ✅ Place orders
- ✅ View order history

### Restaurant Owner Features
- ✅ Manage menu items
- ✅ Upload images (vulnerable to file upload attacks)
- ✅ View and update order status
- ✅ Delete menu items (vulnerable to CSRF)

### Admin Features
- ✅ View all restaurants and orders
- ✅ Manage users
- ✅ Access system logs (vulnerable to command injection)

## 🔍 Vulnerability Summary

| Vulnerability | Status | Location | Severity |
|---------------|--------|----------|----------|
| SQL Injection | ✅ Active | Search functionality | Critical |
| Stored XSS | ✅ Active | Special instructions | High |
| Reflected XSS | ✅ Active | Search results | High |
| CSRF | ✅ Active | Delete menu items | High |
| File Upload | ✅ Active | Image upload | Critical |
| Directory Traversal | ✅ Active | File serving | Medium |
| Weak Passwords | ✅ Active | MD5 hashing | Medium |
| No Rate Limiting | ✅ Active | Login page | Low |
| Command Injection | ✅ Active | Log viewer | Critical |

## 🧪 Testing Tools Ready

The application is ready for testing with:
- **OWASP ZAP**: Web application security scanner
- **Burp Suite**: Web application security testing
- **sqlmap**: Automated SQL injection testing
- **Hydra**: Password brute force testing
- **John the Ripper**: Password hash cracking

## 📚 Documentation

- **README.md**: Complete project overview and setup instructions
- **SECURITY_TESTING_GUIDE.md**: Detailed vulnerability testing guide
- **SETUP_COMPLETE.md**: This setup summary

## 🚨 Security Notice

⚠️ **IMPORTANT**: This application contains deliberate security vulnerabilities for educational purposes only. 

- Do not deploy to production
- Do not expose to the internet
- Use only in controlled, isolated environments
- Practice ethical hacking only

## 🎯 Next Steps

1. **Explore the Application**: Visit http://localhost:5000 and test all features
2. **Practice Exploitation**: Use the security testing guide to practice ethical hacking
3. **Learn Remediation**: Study how to fix each vulnerability
4. **Share Knowledge**: Use this as a teaching tool for cybersecurity education

## 🔧 Troubleshooting

### If the application stops:
```bash
cd /home/berne4321/Vuln_FoodOrder
venv/bin/python app.py
```

### If database is corrupted:
```bash
python init_db.py
```

### If dependencies are missing:
```bash
venv/bin/pip install -r requirements.txt
```

---

**Happy Ethical Hacking! 🎓**

Remember: Always practice responsible disclosure and only test systems you own or have permission to test.
