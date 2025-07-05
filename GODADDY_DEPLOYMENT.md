# GoDaddy Shared Hosting Deployment Guide

## ⚠️ Important Notice

GoDaddy shared hosting has significant limitations for Flask applications:
- Limited Python library support
- No face recognition capabilities
- Restricted file permissions
- Limited database options

**This guide creates a simplified version without face recognition.**

---

## 📋 Step 1: Prepare Simplified Version

### 1.1 Create Simplified Requirements
```text
# requirements-godaddy.txt
Flask==3.0.0
Werkzeug==3.0.1
Pillow==10.1.0
python-dotenv==1.0.0
```

### 1.2 Modify app.py for Shared Hosting
Create `app_godaddy.py` with face recognition disabled:

```python
# At the top of app.py, add:
import os
FACE_RECOGNITION_ENABLED = False

# Replace any face recognition imports with:
try:
    import cv2
    import face_recognition
    FACE_RECOGNITION_ENABLED = True
except ImportError:
    FACE_RECOGNITION_ENABLED = False
    print("Face recognition disabled - libraries not available")
```

---

## 📋 Step 2: GoDaddy cPanel Setup

### 2.1 Access cPanel
1. Log into your GoDaddy account
2. Go to "My Products"
3. Find your hosting account
4. Click "Manage" → "cPanel"

### 2.2 Check Python Support
1. Look for "Python" in cPanel
2. Check available Python versions
3. Note: Many shared hosting plans don't support Python web apps

---

## 📋 Step 3: Alternative Approaches

### Option A: Static HTML Version
Convert your Flask app to static HTML files:
1. Pre-generate all pages
2. Use JavaScript for interactivity
3. Store data in JSON files

### Option B: PHP Version
Rewrite critical parts in PHP:
1. Student management
2. Basic attendance tracking
3. File uploads

### Option C: Use Subdomain with Different Hosting
1. Keep main domain on GoDaddy
2. Create subdomain (e.g., attendance.yourdomain.com)
3. Point subdomain to proper Python hosting

---

## 📋 Step 4: Recommended Alternative

### 4.1 PythonAnywhere Subdomain Setup
1. Deploy to PythonAnywhere (free)
2. Use custom domain feature
3. Point attendance.yourdomain.com to PythonAnywhere
4. Keep main site on GoDaddy

### 4.2 Domain Configuration
In GoDaddy DNS:
```
Type: CNAME
Name: attendance
Value: yourusername.pythonanywhere.com
```

---

## 📋 Step 5: If You Must Use GoDaddy

### 5.1 CGI Script Approach
Create `attendance.cgi`:
```python
#!/usr/bin/env python3
import cgi
import cgitb
import os
import sys

# Add your project to Python path
sys.path.insert(0, '/home/username/public_html/attendance')

# Enable CGI error reporting
cgitb.enable()

# Set content type
print("Content-Type: text/html\n")

# Your simplified Flask app logic here
print("<html><body>")
print("<h1>Attendance Tracker</h1>")
print("</body></html>")
```

### 5.2 .htaccess Configuration
```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ attendance.cgi/$1 [L]

# Set Python CGI
AddHandler cgi-script .cgi .py
Options +ExecCGI
```

---

## 🎯 Strong Recommendation

**Don't use GoDaddy shared hosting for this Flask app.**

### Instead, use this approach:
1. **Main website**: Stay on GoDaddy
2. **Attendance system**: Deploy to PythonAnywhere
3. **Domain setup**: attendance.yourdomain.com → PythonAnywhere
4. **Cost**: $0 (free tier) or $5/month
5. **Benefits**: Full functionality, face recognition, easy management

### Why This Works Better:
- ✅ Full Python support
- ✅ Face recognition works
- ✅ Easy file uploads
- ✅ Proper database support
- ✅ Better performance
- ✅ Easier maintenance

---

## 📋 Migration Strategy

### Phase 1: Set Up PythonAnywhere
1. Follow PythonAnywhere deployment guide
2. Get your app running on yourusername.pythonanywhere.com
3. Test all functionality

### Phase 2: Configure Custom Domain
1. In PythonAnywhere, upgrade to Hacker plan ($5/month)
2. Configure custom domain: attendance.yourdomain.com
3. Update DNS in GoDaddy

### Phase 3: Link from Main Site
1. Add link from your main GoDaddy site
2. "Attendance System" → https://attendance.yourdomain.com
3. Users won't know it's hosted elsewhere

---

## 💡 Final Recommendation

**Use PythonAnywhere with custom domain approach:**
- Total cost: $5/month (same as upgrading GoDaddy shared hosting)
- Full functionality including face recognition
- Professional setup
- Easy to maintain
- Better performance

**This gives you the best of both worlds:**
- Keep your main site on GoDaddy
- Get proper Python hosting for your app
- Professional domain setup
- Full feature set

Would you like me to help you set up the PythonAnywhere deployment with custom domain configuration?
