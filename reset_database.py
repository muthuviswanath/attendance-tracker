#!/usr/bin/env python3
"""
Complete database reset script for Attendance Tracker
This script will completely rebuild the database from scratch.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def reset_database():
    """Completely reset and rebuild the database"""
    print("🔄 Resetting Attendance Tracker Database...")
    
    # Backup existing database
    if os.path.exists('attendance.db'):
        backup_name = f'attendance_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        os.rename('attendance.db', backup_name)
        print(f"📦 Existing database backed up as: {backup_name}")
    
    # Create new database
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    try:
        print("🏗️ Building new database schema...")
        
        # Create users table
        print("📝 Creating users table...")
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create system_settings table
        print("📝 Creating system_settings table...")
        cursor.execute('''
            CREATE TABLE system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        ''')
        
        # Create batches table
        print("📝 Creating batches table...")
        cursor.execute('''
            CREATE TABLE batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                start_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create students table
        print("📝 Creating students table...")
        cursor.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                batch_id INTEGER,
                photo_filename TEXT,
                face_encoding TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches (id)
            )
        ''')
        
        # Create courses table
        print("📝 Creating courses table...")
        cursor.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                instructor TEXT,
                credits INTEGER DEFAULT 3,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create enrollments table
        print("📝 Creating enrollments table...")
        cursor.execute('''
            CREATE TABLE enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrollment_date DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (course_id) REFERENCES courses (id),
                UNIQUE(student_id, course_id)
            )
        ''')
        
        # Create attendance table
        print("📝 Creating attendance table...")
        cursor.execute('''
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'present',
                method TEXT DEFAULT 'manual',
                marked_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        # Create batch_course_enrollments table
        print("📝 Creating batch_course_enrollments table...")
        cursor.execute('''
            CREATE TABLE batch_course_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrollment_date DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (batch_id) REFERENCES batches (id),
                FOREIGN KEY (course_id) REFERENCES courses (id),
                UNIQUE(batch_id, course_id)
            )
        ''')
        
        print("✅ All tables created successfully!")
        
        # Insert default admin user
        print("👤 Creating admin user...")
        admin_password = hash_password('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, email, full_name)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', admin_password, 'admin', 'admin@attendancetracker.com', 'System Administrator'))
        
        # Insert system settings
        print("⚙️ Inserting system settings...")
        settings = [
            ('general', 'system_name', 'Attendance Tracker', 'Name of the system'),
            ('general', 'organization_name', 'Educational Institution', 'Name of the organization'),
            ('general', 'timezone', 'UTC', 'System timezone'),
            ('general', 'date_format', '%Y-%m-%d', 'Date format'),
            ('general', 'time_format', '%H:%M:%S', 'Time format'),
            ('general', 'language', 'en', 'System language'),
            ('general', 'theme', 'light', 'System theme'),
            ('general', 'logo_path', '/static/logos/logo.png', 'Path to system logo'),
            ('general', 'favicon_path', '/static/favicon.ico', 'Path to favicon'),
            ('general', 'contact_email', 'support@attendancetracker.com', 'Contact email'),
            ('general', 'contact_phone', '+1-234-567-8900', 'Contact phone'),
            ('general', 'address', '123 Education St, Learning City, LC 12345', 'Organization address'),
            ('attendance', 'default_status', 'present', 'Default attendance status'),
            ('attendance', 'late_threshold', '15', 'Late threshold in minutes'),
            ('attendance', 'absent_threshold', '30', 'Absent threshold in minutes'),
            ('attendance', 'auto_mark_absent', 'true', 'Auto mark absent after threshold'),
            ('attendance', 'allow_manual_override', 'true', 'Allow manual attendance override'),
            ('attendance', 'require_photo', 'false', 'Require photo for attendance'),
            ('face_recognition', 'enabled', 'false', 'Enable face recognition'),
            ('face_recognition', 'tolerance', '0.6', 'Face recognition tolerance'),
            ('face_recognition', 'model', 'hog', 'Face recognition model'),
            ('face_recognition', 'auto_detect', 'true', 'Auto detect faces'),
            ('notifications', 'email_enabled', 'false', 'Enable email notifications'),
            ('notifications', 'sms_enabled', 'false', 'Enable SMS notifications'),
            ('notifications', 'push_enabled', 'false', 'Enable push notifications'),
            ('security', 'session_timeout', '3600', 'Session timeout in seconds'),
            ('security', 'password_min_length', '6', 'Minimum password length'),
            ('security', 'require_password_change', 'false', 'Require password change on first login'),
            ('security', 'max_login_attempts', '5', 'Maximum login attempts'),
            ('backup', 'auto_backup', 'true', 'Enable automatic backups'),
            ('backup', 'backup_frequency', 'daily', 'Backup frequency'),
            ('backup', 'backup_retention', '30', 'Backup retention in days'),
            ('backup', 'backup_location', '/backups/', 'Backup location'),
        ]
        
        for category, key, value, description in settings:
            cursor.execute('''
                INSERT INTO system_settings (category, key, value, description)
                VALUES (?, ?, ?, ?)
            ''', (category, key, value, description))
        
        # Insert sample batch
        print("🎓 Creating sample batch...")
        cursor.execute('''
            INSERT INTO batches (name, code, description, start_date, end_date)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Sample Batch', 'BATCH001', 'Default sample batch for testing', '2024-01-01', '2024-12-31'))
        
        # Insert sample course
        print("📚 Creating sample course...")
        cursor.execute('''
            INSERT INTO courses (course_id, name, description, instructor)
            VALUES (?, ?, ?, ?)
        ''', ('COURSE001', 'Introduction to Programming', 'Basic programming concepts', 'Dr. Smith'))
        
        # Commit all changes
        conn.commit()
        
        # Verify everything
        print("🔍 Verifying database structure...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   • {table}")
        
        # Check admin user
        cursor.execute("SELECT username, role FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        if admin:
            print(f"✅ Admin user: {admin[0]} ({admin[1]})")
        
        # Check system settings
        cursor.execute("SELECT COUNT(*) FROM system_settings")
        settings_count = cursor.fetchone()[0]
        print(f"✅ System settings: {settings_count} entries")
        
        # Test a few key queries
        cursor.execute("SELECT category, key, value FROM system_settings WHERE category = 'general' LIMIT 3")
        sample_settings = cursor.fetchall()
        print(f"✅ Sample settings working: {len(sample_settings)} entries")
        
        print("\n🎉 Database reset completed successfully!")
        print("\n📋 Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n🔧 Next Steps:")
        print("1. Reload your PythonAnywhere web app")
        print("2. Test the login page")
        print("3. Verify all functionality works")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function"""
    print("🔄 Attendance Tracker Database Reset")
    print("=" * 50)
    
    # Confirm reset
    print("⚠️  WARNING: This will completely rebuild your database!")
    print("   - All existing data will be backed up")
    print("   - A fresh database will be created")
    print("   - Default admin user will be created")
    
    if reset_database():
        print("\n✅ Database reset completed successfully!")
    else:
        print("\n❌ Database reset failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
