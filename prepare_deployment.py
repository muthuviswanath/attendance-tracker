#!/usr/bin/env python3
"""
Deployment preparation script for Attendance Tracker
"""

import os
import shutil
import subprocess
import sys

def check_requirements():
    """Check if required tools are installed"""
    print("🔍 Checking requirements...")
    
    # Check if git is installed
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git is installed")
        else:
            print("❌ Git is not installed")
            return False
    except FileNotFoundError:
        print("❌ Git is not installed")
        return False
    
    # Check if Python is installed
    print(f"✅ Python {sys.version}")
    
    return True

def setup_git_repo():
    """Initialize git repository if not already done"""
    print("\n📦 Setting up Git repository...")
    
    if os.path.exists('.git'):
        print("✅ Git repository already exists")
        return True
    
    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], check=True)
        print("✅ Git repository initialized")
        
        # Add all files
        subprocess.run(['git', 'add', '.'], check=True)
        print("✅ Files added to git")
        
        # Create initial commit
        subprocess.run(['git', 'commit', '-m', 'Initial commit for deployment'], check=True)
        print("✅ Initial commit created")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git setup failed: {e}")
        return False

def create_env_file():
    """Create .env file from example"""
    print("\n⚙️ Setting up environment file...")
    
    if os.path.exists('.env'):
        print("✅ .env file already exists")
        return True
    
    if os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print("✅ .env file created from example")
        print("⚠️  Remember to update .env with your actual values!")
        return True
    else:
        print("❌ .env.example not found")
        return False

def check_database():
    """Check if database exists and is accessible"""
    print("\n🗄️ Checking database...")
    
    if os.path.exists('attendance.db'):
        print("✅ Database file exists")
        
        # Try to connect to database
        try:
            import sqlite3
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            if tables:
                print(f"✅ Database has {len(tables)} tables")
                return True
            else:
                print("⚠️  Database exists but has no tables")
                return False
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    else:
        print("❌ Database file not found")
        return False

def check_static_files():
    """Check static files structure"""
    print("\n📁 Checking static files...")
    
    static_dir = 'static'
    photos_dir = 'static/student_photos'
    
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print("✅ Static directory created")
    
    if not os.path.exists(photos_dir):
        os.makedirs(photos_dir)
        print("✅ Student photos directory created")
    
    # Check if photos exist
    if os.path.exists(photos_dir):
        photos = [f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        if photos:
            print(f"✅ Found {len(photos)} photo files")
        else:
            print("⚠️  No photo files found")
    
    return True

def display_deployment_options():
    """Show deployment options to user"""
    print("\n" + "="*60)
    print("🚀 DEPLOYMENT OPTIONS")
    print("="*60)
    
    print("\n1. 🌟 PythonAnywhere (RECOMMENDED)")
    print("   • Full Python support")
    print("   • Face recognition works")
    print("   • Free tier available")
    print("   • Easy deployment")
    print("   • Guide: PYTHONANYWHERE_DEPLOYMENT.md")
    
    print("\n2. 🔧 Heroku")
    print("   • Git-based deployment")
    print("   • Good for developers")
    print("   • May need external storage")
    print("   • Face recognition may be limited")
    
    print("\n3. 💻 GoDaddy VPS")
    print("   • Full control")
    print("   • Expensive")
    print("   • Requires server management")
    print("   • All features work")
    
    print("\n4. ⚠️  GoDaddy Shared Hosting")
    print("   • Limited functionality")
    print("   • No face recognition")
    print("   • Not recommended")
    print("   • Guide: GODADDY_DEPLOYMENT.md")
    
    print("\n" + "="*60)
    print("💡 RECOMMENDATION: Use PythonAnywhere")
    print("="*60)

def main():
    """Main deployment preparation function"""
    print("🎯 ATTENDANCE TRACKER - DEPLOYMENT PREPARATION")
    print("="*60)
    
    success = True
    
    # Check requirements
    if not check_requirements():
        success = False
    
    # Setup git repository
    if not setup_git_repo():
        success = False
    
    # Create environment file
    if not create_env_file():
        success = False
    
    # Check database
    if not check_database():
        success = False
    
    # Check static files
    if not check_static_files():
        success = False
    
    # Display results
    print("\n" + "="*60)
    if success:
        print("✅ PREPARATION COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️  PREPARATION COMPLETED WITH WARNINGS")
    print("="*60)
    
    # Show deployment options
    display_deployment_options()
    
    print("\n📋 NEXT STEPS:")
    print("1. Choose your hosting platform")
    print("2. Follow the appropriate deployment guide")
    print("3. Update your .env file with production values")
    print("4. Test your deployment")
    
    print("\n📚 AVAILABLE GUIDES:")
    print("• PYTHONANYWHERE_DEPLOYMENT.md - Detailed PythonAnywhere setup")
    print("• GODADDY_DEPLOYMENT.md - GoDaddy options and alternatives")
    print("• HOSTING_RECOMMENDATIONS.md - Platform comparison")
    
    print("\n🆘 NEED HELP?")
    print("Choose a deployment option and I'll help you with the specific steps!")

if __name__ == "__main__":
    main()
