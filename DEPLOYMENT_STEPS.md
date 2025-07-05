# Step-by-Step PythonAnywhere Deployment

## 🎯 Current Status
✅ Git repository initialized
✅ All files committed
✅ Configuration files ready
✅ Database and photos ready

## 🚀 Step 1: Create GitHub Repository

### 1.1 Go to GitHub
1. Open your browser and go to [GitHub.com](https://github.com)
2. Sign in to your account
3. Click the "+" icon in the top right
4. Select "New repository"

### 1.2 Create Repository
1. **Repository name**: `attendance-tracker`
2. **Description**: `Flask-based attendance tracking system with facial recognition`
3. **Visibility**: Choose Public or Private
4. **DO NOT** check any boxes (no README, no .gitignore, no license)
5. Click "Create repository"

### 1.3 Copy Repository URL
GitHub will show you the repository URL. Copy it for the next step.
Example: `https://github.com/yourusername/attendance-tracker.git`

## 🚀 Step 2: Push Code to GitHub

Open your terminal/command prompt in the AttendanceTracker directory and run these commands:

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/yourusername/attendance-tracker.git

# Push your code to GitHub
git branch -M main
git push -u origin main
```

**Wait for this to complete before proceeding to Step 3!**

---

## 🚀 Step 3: Create PythonAnywhere Account

### 3.1 Sign Up
1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com)
2. Click "Pricing & signup"
3. Choose "Create a Beginner account" (Free)
4. Fill out the form:
   - Username (remember this - it will be in your URL)
   - Email
   - Password
5. Verify your email

### 3.2 Login
1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com)
2. Click "Log in"
3. Enter your credentials

---

## 🚀 Step 4: Set Up Your Code on PythonAnywhere

### 4.1 Open Bash Console
1. In your PythonAnywhere dashboard
2. Click on "Tasks" menu
3. Click "Consoles"
4. Click "Bash" to start a new console

### 4.2 Clone Your Repository
In the Bash console, run:

```bash
# Clone your repository
git clone https://github.com/yourusername/attendance-tracker.git

# Navigate to the directory
cd attendance-tracker

# Check that files are there
ls -la
```

---

## 🚀 Step 5: Set Up Virtual Environment

In the same Bash console:

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements-production.txt
```

**This may take a few minutes. Wait for it to complete.**

---

## 🚀 Step 6: Install Face Recognition Libraries

```bash
# Install additional libraries for face recognition
pip install opencv-python-headless
pip install dlib
pip install face-recognition

# Install other useful libraries
pip install python-dotenv
```

**This step may take 5-10 minutes. Be patient!**

---

## 🚀 Step 7: Set Up Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit the .env file
nano .env
```

Update the .env file with these values:
```
SECRET_KEY=your-very-secure-secret-key-change-this-now
FLASK_ENV=production
DEBUG=false
DATABASE_PATH=/home/yourusername/attendance-tracker/attendance.db
UPLOAD_FOLDER=/home/yourusername/attendance-tracker/static/student_photos
FACE_RECOGNITION_ENABLED=true
LOG_TO_STDOUT=true
```

Replace `yourusername` with your actual PythonAnywhere username.

Save and exit nano (Ctrl+X, then Y, then Enter).

---

## 🚀 Step 8: Set Up Database

```bash
# Create necessary directories
mkdir -p logs
mkdir -p backups

# Initialize database
python3 -c "
import sqlite3
import os

# Create database
conn = sqlite3.connect('attendance.db')
print('Database created successfully')

# Test connection
cursor = conn.cursor()
cursor.execute('SELECT 1')
print('Database connection test successful')
conn.close()
"
```

---

## 🚀 Step 9: Configure Web App

### 9.1 Create Web App
1. Go to the "Web" tab in your PythonAnywhere dashboard
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select "Python 3.10"
5. Click "Next"

### 9.2 Set Source Code Directory
1. In the "Code" section, find "Source code"
2. Set it to: `/home/yourusername/attendance-tracker`
3. Click the checkmark to save

### 9.3 Set Virtual Environment
1. In the "Virtualenv" section
2. Set it to: `/home/yourusername/attendance-tracker/venv`
3. Click the checkmark to save

### 9.4 Configure WSGI File
1. Click on the WSGI configuration file link
2. Delete all content and replace with:

```python
import sys
import os

# Add your project directory to the sys.path
path = '/home/yourusername/attendance-tracker'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
```

3. Replace `yourusername` with your actual username
4. Save the file (Ctrl+S)

---

## 🚀 Step 10: Configure Static Files

### 10.1 Set Static Files Mapping
1. In the "Static files" section of the Web tab
2. Click "Add a new static file mapping"
3. Set:
   - **URL**: `/static/`
   - **Directory**: `/home/yourusername/attendance-tracker/static/`
4. Click the checkmark to save

---

## 🚀 Step 11: Set File Permissions

Back in the Bash console:

```bash
# Set proper permissions
chmod 755 /home/yourusername/attendance-tracker
chmod 644 attendance.db
chmod 755 static/student_photos
chmod 644 static/student_photos/*
```

---

## 🚀 Step 12: Test and Launch

### 12.1 Test the Application
In the Bash console:

```bash
# Test that the app can start
python3 -c "
from app import app
print('Flask app imported successfully')
with app.test_client() as client:
    response = client.get('/')
    print(f'Test response status: {response.status_code}')
"
```

### 12.2 Reload Web App
1. Go back to the "Web" tab
2. Click the big green "Reload yourusername.pythonanywhere.com" button
3. Wait for the reload to complete

### 12.3 Test Your Site
1. Click on the link to your site: `https://yourusername.pythonanywhere.com`
2. Your attendance tracker should be live!

---

## 🎉 Congratulations!

If everything worked, your attendance tracker is now live on the internet!

---

**Ready to start with Step 1? Create your GitHub repository and let me know when you're ready for the next step!**
