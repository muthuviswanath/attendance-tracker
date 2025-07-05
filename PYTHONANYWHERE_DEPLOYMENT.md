# PythonAnywhere Deployment Guide

## 🎯 Step-by-Step Deployment to PythonAnywhere

### Prerequisites
- PythonAnywhere account (free tier works)
- Your code on GitHub
- This deployment guide

---

## 📋 Step 1: Prepare Your Code

### 1.1 Create GitHub Repository
```bash
# In your project directory
git init
git add .
git commit -m "Initial commit for deployment"

# Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/attendance-tracker.git
git branch -M main
git push -u origin main
```

### 1.2 Create .env File
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FACE_RECOGNITION_ENABLED=true
DATABASE_PATH=/home/yourusername/attendance.db
UPLOAD_FOLDER=/home/yourusername/static/student_photos
```

---

## 📋 Step 2: Set Up PythonAnywhere

### 2.1 Create Account
1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com/)
2. Sign up for free account
3. Verify email and log in

### 2.2 Open Bash Console
1. Go to "Tasks" → "Consoles"
2. Start a new Bash console

---

## 📋 Step 3: Clone and Set Up Your Code

### 3.1 Clone Repository
```bash
# In PythonAnywhere bash console
git clone https://github.com/yourusername/attendance-tracker.git
cd attendance-tracker
```

### 3.2 Create Virtual Environment
```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3.3 Install Dependencies
```bash
# Install production requirements
pip install -r requirements-production.txt

# If face recognition is needed (may take time)
pip install opencv-python dlib face-recognition
```

---

## 📋 Step 4: Configure Web App

### 4.1 Create Web App
1. Go to "Web" tab in PythonAnywhere dashboard
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select "Python 3.10"

### 4.2 Configure WSGI File
1. In Web tab, click on WSGI configuration file
2. Replace contents with:

```python
import sys
import os

# Add your project directory to Python path
path = '/home/yourusername/attendance-tracker'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Import your application
from app import app as application

# For debugging (remove in production)
if __name__ == "__main__":
    application.run()
```

### 4.3 Set Virtual Environment Path
1. In Web tab, find "Virtualenv" section
2. Enter: `/home/yourusername/attendance-tracker/venv`

---

## 📋 Step 5: Configure Static Files

### 5.1 Set Static Files Mapping
1. In Web tab, find "Static files" section
2. Add mapping:
   - **URL**: `/static/`
   - **Directory**: `/home/yourusername/attendance-tracker/static/`

### 5.2 Create Required Directories
```bash
# In bash console
mkdir -p static/student_photos
mkdir -p logs
mkdir -p backups
```

---

## 📋 Step 6: Database Setup

### 6.1 Create Database
```bash
# In bash console, in your project directory
python3 -c "
import sqlite3
conn = sqlite3.connect('attendance.db')
conn.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY)')
conn.close()
print('Database created successfully')
"
```

### 6.2 Run Database Initialization
```bash
# If you have a database setup script
python3 reset_db.py

# Or manually create tables using your app
python3 -c "
from app import init_db
init_db()
print('Database initialized')
"
```

---

## 📋 Step 7: Configure Environment

### 7.1 Create .env File
```bash
# Create .env file in your project directory
cat > .env << 'EOF'
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
DEBUG=false
DATABASE_PATH=/home/yourusername/attendance-tracker/attendance.db
UPLOAD_FOLDER=/home/yourusername/attendance-tracker/static/student_photos
FACE_RECOGNITION_ENABLED=true
LOG_TO_STDOUT=true
EOF
```

### 7.2 Set File Permissions
```bash
chmod 600 .env
chmod 664 attendance.db
chmod 755 static/student_photos
```

---

## 📋 Step 8: Test and Deploy

### 8.1 Test Application
```bash
# In bash console
python3 -c "
from app import app
with app.test_client() as client:
    response = client.get('/')
    print(f'Status: {response.status_code}')
    print('App is working!' if response.status_code == 200 else 'App has issues')
"
```

### 8.2 Reload Web App
1. Go to Web tab
2. Click "Reload yourusername.pythonanywhere.com"
3. Wait for reload to complete

### 8.3 Test in Browser
1. Visit: `https://yourusername.pythonanywhere.com`
2. Test all functionality
3. Check for any errors

---

## 📋 Step 9: Post-Deployment Setup

### 9.1 Upload Initial Data
```bash
# Copy your sample data if needed
python3 add_sample_data.py
```

### 9.2 Test File Uploads
1. Try uploading a student photo
2. Check if face recognition works
3. Verify attendance marking

### 9.3 Set Up Monitoring
1. Check logs: `tail -f logs/attendance_system.log`
2. Monitor error logs in PythonAnywhere dashboard

---

## 🔧 Troubleshooting

### Common Issues:

**1. Import Errors**
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Verify modules
pip list | grep -i flask
```

**2. Database Errors**
```bash
# Check database permissions
ls -la attendance.db

# Test database connection
python3 -c "
import sqlite3
conn = sqlite3.connect('attendance.db')
print('Database connection successful')
conn.close()
"
```

**3. Static Files Not Loading**
- Check static files mapping in Web tab
- Verify file permissions
- Test direct URL access

**4. Face Recognition Issues**
```bash
# Test OpenCV installation
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"

# Test face recognition
python3 -c "import face_recognition; print('Face recognition available')"
```

---

## 🎉 Success!

Your attendance tracker should now be live at:
`https://yourusername.pythonanywhere.com`

### Next Steps:
1. **Configure your domain** (if you have one)
2. **Set up regular backups**
3. **Monitor performance**
4. **Add more students and courses**

### Support:
- PythonAnywhere help: [help.pythonanywhere.com](https://help.pythonanywhere.com/)
- Flask documentation: [flask.palletsprojects.com](https://flask.palletsprojects.com/)

**Your attendance tracker is now live and ready to use!** 🚀
