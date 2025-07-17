import os
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, g, session
import cv2
import numpy as np
from PIL import Image
from datetime import datetime, date, timedelta
import base64
from werkzeug.utils import secure_filename
import pickle
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['DATABASE'] = 'attendance.db'

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)  # 5 minutes idle timeout
app.config['UPLOAD_FOLDER'] = 'static/student_photos'

# Logging configuration
if not app.debug:
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/attendance_system.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Attendance Tracker System startup')
else:
    # Also log in debug mode for development
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/attendance_system.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Attendance Tracker System startup (DEBUG mode)')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Logging helper function
def log_user_action(action, details="", resource_type="", resource_id="", status="SUCCESS"):
    """
    Log user actions consistently throughout the application.
    
    Args:
        action (str): The action performed (e.g., "CREATE", "UPDATE", "DELETE", "VIEW")
        details (str): Additional details about the action
        resource_type (str): Type of resource affected (e.g., "STUDENT", "COURSE", "BATCH")
        resource_id (str): ID or identifier of the resource
        status (str): Status of the action ("SUCCESS", "FAILED", "WARNING")
    """
    username = session.get('username', 'ANONYMOUS')
    user_role = session.get('role', 'UNKNOWN')
    
    log_message = f"USER_ACTION | User: {username} ({user_role}) | Action: {action}"
    
    if resource_type:
        log_message += f" | Resource: {resource_type}"
    
    if resource_id:
        log_message += f" | ID: {resource_id}"
    
    if details:
        log_message += f" | Details: {details}"
    
    log_message += f" | Status: {status}"
    
    if status == "SUCCESS":
        app.logger.info(log_message)
    elif status == "WARNING":
        app.logger.warning(log_message)
    else:  # FAILED or ERROR
        app.logger.error(log_message)

# Database helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        
        # First, create tables without constraints
        db.executescript('''
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_name TEXT UNIQUE NOT NULL,
                batch_year INTEGER NOT NULL,
                description TEXT,
                min_attendance_percentage REAL DEFAULT 75.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                photo_path TEXT,
                face_encoding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE NOT NULL,
                course_name TEXT NOT NULL,
                instructor TEXT NOT NULL,
                schedule TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                course_id INTEGER,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                course_id INTEGER,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status TEXT DEFAULT 'Present',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            
            CREATE TABLE IF NOT EXISTS batch_course_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,
                course_id INTEGER,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_mandatory BOOLEAN DEFAULT 1,
                FOREIGN KEY (batch_id) REFERENCES batches (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, setting_key)
            );
            
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'attendance_taker')),
                full_name TEXT NOT NULL,
                email TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        ''')
        db.commit()
        
        # Run migration to add new columns
        migrate_existing_data()

def migrate_existing_data():
    """Migrate existing data to new schema"""
    db = get_db()
    
    try:
        # Add new columns to students table
        try:
            db.execute('ALTER TABLE students ADD COLUMN batch_id INTEGER')
            print("Added batch_id column to students table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding batch_id to students: {e}")
        
        # Add new columns to courses table
        try:
            db.execute('ALTER TABLE courses ADD COLUMN parent_course_id INTEGER')
            print("Added parent_course_id column to courses table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding parent_course_id to courses: {e}")
        
        try:
            db.execute('ALTER TABLE courses ADD COLUMN course_level INTEGER DEFAULT 1')
            print("Added course_level column to courses table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding course_level to courses: {e}")
        
        try:
            db.execute('ALTER TABLE courses ADD COLUMN min_attendance_percentage REAL DEFAULT 75.0')
            print("Added min_attendance_percentage column to courses table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding min_attendance_percentage to courses: {e}")
        
        try:
            db.execute('ALTER TABLE courses ADD COLUMN is_active BOOLEAN DEFAULT 1')
            print("Added is_active column to courses table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding is_active to courses: {e}")
        
        # Add new columns to enrollments table
        try:
            db.execute('ALTER TABLE enrollments ADD COLUMN enrollment_type TEXT DEFAULT "direct"')
            print("Added enrollment_type column to enrollments table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding enrollment_type to enrollments: {e}")
        
        try:
            db.execute('ALTER TABLE enrollments ADD COLUMN is_active BOOLEAN DEFAULT 1')
            print("Added is_active column to enrollments table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding is_active to enrollments: {e}")
        
        # Add new columns to attendance table
        try:
            db.execute('ALTER TABLE attendance ADD COLUMN attendance_type TEXT DEFAULT "direct"')
            print("Added attendance_type column to attendance table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Error adding attendance_type to attendance: {e}")
        
        # Create default batch if none exists
        default_batch_check = db.execute('SELECT COUNT(*) FROM batches').fetchone()[0]
        if default_batch_check == 0:
            db.execute('''
                INSERT INTO batches (batch_name, batch_year, description, min_attendance_percentage)
                VALUES ('Default Batch', ?, 'Auto-created for existing students', 75.0)
            ''', (datetime.now().year,))
            print("Created default batch")
        
        # Update existing students to have a batch_id if they don't have one
        students_without_batch = db.execute('SELECT COUNT(*) FROM students WHERE batch_id IS NULL').fetchone()[0]
        if students_without_batch > 0:
            default_batch = db.execute('SELECT id FROM batches WHERE batch_name = "Default Batch"').fetchone()
            if default_batch:
                db.execute('UPDATE students SET batch_id = ? WHERE batch_id IS NULL', (default_batch[0],))
                print(f"Updated {students_without_batch} students to use default batch")
        
        # Update existing courses to have proper defaults
        db.execute('UPDATE courses SET course_level = 1 WHERE course_level IS NULL')
        db.execute('UPDATE courses SET min_attendance_percentage = 75.0 WHERE min_attendance_percentage IS NULL')
        db.execute('UPDATE courses SET is_active = 1 WHERE is_active IS NULL')
        
        # Update existing enrollments
        db.execute('UPDATE enrollments SET enrollment_type = "direct" WHERE enrollment_type IS NULL')
        db.execute('UPDATE enrollments SET is_active = 1 WHERE is_active IS NULL')
        
        # Update existing attendance records
        db.execute('UPDATE attendance SET attendance_type = "direct" WHERE attendance_type IS NULL')
        
        # Initialize default system settings if not exists
        default_settings = [
            ('general', 'institution_name', 'Your Institution'),
            ('general', 'academic_year', str(datetime.now().year) + '-' + str(datetime.now().year + 1)),
            ('general', 'current_semester', 'Fall'),
            ('general', 'default_attendance_threshold', '75.0'),
            ('attendance', 'grace_period_minutes', '10'),
            ('attendance', 'calculation_method', 'percentage'),
            ('attendance', 'auto_aggregate_main_courses', 'true'),
            ('attendance', 'low_attendance_threshold', '50.0'),
            ('batch', 'naming_convention', 'year_only'),
            ('batch', 'auto_create_batches', 'false'),
            ('batch', 'promotion_threshold', '75.0')
        ]
        
        for category, key, value in default_settings:
            existing = db.execute(
                'SELECT id FROM system_settings WHERE category = ? AND setting_key = ?',
                (category, key)
            ).fetchone()
            
            if not existing:
                db.execute(
                    'INSERT INTO system_settings (category, setting_key, setting_value) VALUES (?, ?, ?)',
                    (category, key, value)
                )
        
        # Create default admin user if no users exist
        user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if user_count == 0:
            admin_password = hash_password('admin123')
            db.execute('''
                INSERT INTO users (username, password_hash, role, full_name, email, is_active)
                VALUES ('admin', ?, 'admin', 'System Administrator', 'admin@institution.edu', 1)
            ''', (admin_password,))
            print("Created default admin user: admin/admin123")
            
            # Also create a sample attendance taker
            taker_password = hash_password('taker123')
            db.execute('''
                INSERT INTO users (username, password_hash, role, full_name, email, is_active)
                VALUES ('attendance_taker', ?, 'attendance_taker', 'Attendance Officer', 'taker@institution.edu', 1)
            ''', (taker_password,))
            print("Created sample attendance taker: attendance_taker/taker123")
        
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        db.rollback()
        raise

# Authentication Helper Functions

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    """Check if a password matches its hash"""
    return hash_password(password) == hashed

def login_required(f):
    """Decorator to require login for a route with session timeout check"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check session timeout (5 minutes)
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=5):
                session.clear()
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role with session timeout check"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check session timeout (5 minutes)
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=5):
                session.clear()
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
        # Check admin role
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def attendance_taker_required(f):
    """Decorator to allow both admin and attendance_taker roles with session timeout check"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check session timeout (5 minutes)
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=5):
                session.clear()
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
        # Check role permissions
        if session.get('role') not in ['admin', 'attendance_taker']:
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        db = get_db()
        return db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return None

# Core Business Logic Functions for Hierarchical Courses and Batch Management

def get_main_courses():
    """Get all main courses (level 1)"""
    db = get_db()
    return db.execute(
        'SELECT * FROM courses WHERE course_level = 1 AND is_active = 1 ORDER BY course_name'
    ).fetchall()

def get_sub_courses(parent_course_id):
    """Get all sub-courses for a given main course"""
    db = get_db()
    return db.execute(
        'SELECT * FROM courses WHERE parent_course_id = ? AND course_level = 2 AND is_active = 1 ORDER BY course_name',
        (parent_course_id,)
    ).fetchall()

def get_course_hierarchy():
    """Get complete course hierarchy as list of tuples"""
    main_courses = get_main_courses()
    hierarchy = []
    
    for main_course in main_courses:
        sub_courses = get_sub_courses(main_course['id'])
        hierarchy.append((dict(main_course), [dict(sub) for sub in sub_courses]))
    
    return hierarchy

def calculate_main_course_attendance(student_id, main_course_id):
    """Calculate main course attendance from sub-courses with equal weights"""
    db = get_db()
    
    # Get all sub-courses for this main course
    sub_courses = get_sub_courses(main_course_id)
    
    if not sub_courses:
        # If no sub-courses, check direct attendance on main course
        return calculate_direct_attendance(student_id, main_course_id)
    
    total_attendance = 0
    total_classes = 0
    
    for sub_course in sub_courses:
        attendance_data = calculate_direct_attendance(student_id, sub_course['id'])
        if attendance_data['total_classes'] > 0:
            total_attendance += attendance_data['attended_classes']
            total_classes += attendance_data['total_classes']
    
    if total_classes == 0:
        return {'attended_classes': 0, 'total_classes': 0, 'percentage': 0.0}
    
    percentage = (total_attendance / total_classes) * 100
    return {
        'attended_classes': total_attendance,
        'total_classes': total_classes,
        'percentage': round(percentage, 2)
    }

def calculate_direct_attendance(student_id, course_id):
    """Calculate direct attendance for a specific course"""
    db = get_db()
    
    # Get total classes for this course
    total_classes = db.execute(
        'SELECT COUNT(DISTINCT date) FROM attendance WHERE course_id = ?',
        (course_id,)
    ).fetchone()[0]
    
    # Get attended classes for this student
    attended_classes = db.execute(
        '''SELECT COUNT(DISTINCT date) FROM attendance 
           WHERE course_id = ? AND student_id = ? AND status = 'Present' ''',
        (course_id, student_id)
    ).fetchone()[0]
    
    percentage = (attended_classes / total_classes * 100) if total_classes > 0 else 0
    
    return {
        'attended_classes': attended_classes,
        'total_classes': total_classes,
        'percentage': round(percentage, 2)
    }

def mark_attendance_with_aggregation(student_id, course_id, date, time, status='Present'):
    """Mark attendance and immediately update main course aggregation"""
    db = get_db()
    
    # Convert time to string if it's a time object
    if hasattr(time, 'strftime'):
        time_str = time.strftime('%H:%M:%S')
    else:
        time_str = str(time)
    
    # Get student and course info for logging
    student = db.execute('SELECT name, student_id FROM students WHERE id = ?', (student_id,)).fetchone()
    course = db.execute('SELECT course_name, parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    # Mark direct attendance
    db.execute(
        '''INSERT OR REPLACE INTO attendance 
           (student_id, course_id, date, time, status, attendance_type)
           VALUES (?, ?, ?, ?, ?, 'direct')''',
        (student_id, course_id, date, time_str, status)
    )
    
    app.logger.info(f'Attendance marked: {student["name"]} ({student["student_id"]}) - {status} for {course["course_name"]} on {date}')
    
    # If this is a sub-course, update main course aggregated attendance
    if course and course['parent_course_id']:
        main_course_id = course['parent_course_id']
        attendance_data = calculate_main_course_attendance(student_id, main_course_id)
        
        # Update or insert aggregated attendance for main course
        db.execute(
            '''INSERT OR REPLACE INTO attendance 
               (student_id, course_id, date, time, status, attendance_type)
               VALUES (?, ?, ?, ?, ?, 'aggregated')''',
            (student_id, main_course_id, date, time_str, 
             'Present' if attendance_data['percentage'] >= 75 else 'Absent')
        )
        
        main_course = db.execute('SELECT course_name FROM courses WHERE id = ?', (main_course_id,)).fetchone()
        app.logger.info(f'Main course attendance updated: {student["name"]} - {main_course["course_name"]} - {attendance_data["percentage"]:.1f}%')
    
    db.commit()

def get_student_batches():
    """Get all batches"""
    db = get_db()
    return db.execute('SELECT * FROM batches ORDER BY batch_year DESC, batch_name').fetchall()

def enroll_student_with_batch_priority(student_id, course_id):
    """Enroll student considering batch rules priority"""
    db = get_db()
    
    # Validate that this is a sub-course (students can only enroll in sub-courses)
    course = db.execute('SELECT parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course or course['parent_course_id'] is None:
        raise ValueError('Students can only be enrolled in sub-courses, not main courses.')
    
    # Get student's batch
    student = db.execute('SELECT batch_id FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if not student or not student['batch_id']:
        # Direct enrollment if no batch
        return enroll_student_direct(student_id, course_id)
    
    batch_id = student['batch_id']
    
    # Check if batch has enrollment for this course
    batch_enrollment = db.execute(
        'SELECT * FROM batch_course_enrollments WHERE batch_id = ? AND course_id = ?',
        (batch_id, course_id)
    ).fetchone()
    
    enrollment_type = 'batch_inherited' if batch_enrollment else 'direct'
    
    # Enroll student (validation already done above)
    db.execute(
        '''INSERT OR REPLACE INTO enrollments 
           (student_id, course_id, enrollment_type, is_active)
           VALUES (?, ?, ?, 1)''',
        (student_id, course_id, enrollment_type)
    )
    db.commit()
    
    return True

def enroll_student_direct(student_id, course_id):
    """Direct student enrollment"""
    db = get_db()
    
    # Validate that this is a sub-course (students can only enroll in sub-courses)
    course = db.execute('SELECT parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course or course['parent_course_id'] is None:
        raise ValueError('Students can only be enrolled in sub-courses, not main courses.')
    
    db.execute(
        '''INSERT OR REPLACE INTO enrollments 
           (student_id, course_id, enrollment_type, is_active)
           VALUES (?, ?, 'direct', 1)''',
        (student_id, course_id)
    )
    db.commit()
    return True

# Face Recognition Class (Simplified version using OpenCV)
# Face Recognition Class (using OpenCV with template matching)
class FaceRecognizer:
    def __init__(self):
        self.known_face_templates = []
        self.known_face_names = []
        self.known_face_student_ids = []
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load all student face templates from database"""
        app.logger.info("Loading known faces for recognition...")
        db = get_db()
        students = db.execute(
            'SELECT id, student_id, name, photo_path FROM students WHERE photo_path IS NOT NULL'
        ).fetchall()
        
        self.known_face_templates = []
        self.known_face_names = []
        self.known_face_student_ids = []
        
        loaded_count = 0
        
        for student in students:
            if student['photo_path']:
                # Construct full path to photo
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student['photo_path'])
                
                if os.path.exists(photo_path):
                    try:
                        # Load image
                        image = cv2.imread(photo_path)
                        if image is not None:
                            # Convert to grayscale
                            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                            
                            # Detect faces in the student photo
                            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                            
                            if len(faces) > 0:
                                # Use the first (largest) face found
                                (x, y, w, h) = faces[0]
                                face_template = gray[y:y+h, x:x+w]
                                
                                # Resize to standard size for better matching
                                face_template = cv2.resize(face_template, (100, 100))
                                
                                self.known_face_templates.append(face_template)
                                self.known_face_names.append(student['name'])
                                self.known_face_student_ids.append(student['id'])
                                loaded_count += 1
                                app.logger.info(f"Loaded face template for: {student['name']} ({student['student_id']})")
                            else:
                                app.logger.warning(f"No face found in photo for student: {student['name']} ({student['student_id']})")
                        else:
                            app.logger.warning(f"Could not load image for student: {student['name']} - {photo_path}")
                    except Exception as e:
                        app.logger.error(f"Error loading face template for {student['name']}: {str(e)}")
                else:
                    app.logger.warning(f"Photo file not found for student: {student['name']} - {photo_path}")
        
        app.logger.info(f"Total face templates loaded: {loaded_count}")
    
    def recognize_faces(self, frame):
        """Detect and recognize faces in the given frame"""
        app.logger.info("Starting face recognition...")
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        recognized_students = []
        face_locations = []
        
        app.logger.info(f"Detected {len(faces)} faces")
        
        for i, (x, y, w, h) in enumerate(faces):
            # Extract face from frame
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (100, 100))
            
            # Convert to face_locations format for consistency
            face_locations.append((y, x+w, y+h, x))
            
            best_match = None
            best_score = float('inf')
            
            # Compare with known face templates
            for j, template in enumerate(self.known_face_templates):
                try:
                    # Use template matching
                    result = cv2.matchTemplate(face_roi, template, cv2.TM_SQDIFF_NORMED)
                    _, min_val, _, _ = cv2.minMaxLoc(result)
                    
                    if min_val < best_score:
                        best_score = min_val
                        best_match = j
                        
                except Exception as e:
                    app.logger.error(f"Error in template matching: {str(e)}")
                    continue
            
            # If we found a good match (low difference score)
            if best_match is not None and best_score < 0.5:  # Threshold for recognition
                student_id = self.known_face_student_ids[best_match]
                student_name = self.known_face_names[best_match]
                confidence = 1 - best_score  # Convert to confidence score
                
                recognized_students.append({
                    'student_id': student_id,
                    'name': student_name,
                    'confidence': confidence
                })
                app.logger.info(f"Recognized student: {student_name} (ID: {student_id}) with confidence: {confidence:.2f}")
            else:
                app.logger.info(f"Face {i+1} detected but not recognized (best score: {best_score:.3f})")
        
        app.logger.info(f"Final recognized students: {len(recognized_students)}")
        return recognized_students, face_locations

# Initialize face recognizer within app context
face_recognizer = None

def init_face_recognizer():
    global face_recognizer
    face_recognizer = FaceRecognizer()

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        app.logger.info(f'Login attempt for username: {username}')
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ? AND is_active = 1',
            (username,)
        ).fetchone()
        
        if user and check_password(password, user['password_hash']):
            session.permanent = True  # Enable permanent session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            session['last_activity'] = datetime.now().isoformat()  # Set initial activity time
            
            # Update last login
            db.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().isoformat(), user['id'])
            )
            db.commit()
            
            app.logger.info(f'Successful login for user: {username} ({user["full_name"]})')
            flash(f'Welcome, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            app.logger.warning(f'Failed login attempt for username: {username}')
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    app.logger.info(f'User logout: {username}')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """Landing page - redirect to login if not authenticated, otherwise to dashboard"""
    if 'user_id' in session:
        # Check session timeout
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=5):
                session.clear()
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard after login"""
    return render_template('index.html')

@app.route('/students')
@admin_required
def students():
    # Log page access
    log_user_action("VIEW", "Accessed student management page", "PAGE", "students")
    
    db = get_db()
    students = db.execute('''
        SELECT s.*, b.batch_name 
        FROM students s 
        LEFT JOIN batches b ON s.batch_id = b.id 
        ORDER BY s.created_at DESC
    ''').fetchall()
    batches = get_student_batches()
    return render_template('students.html', students=students, batches=batches)

@app.route('/add_student', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        email = request.form['email']
        batch_id = request.form.get('batch_id')
        
        app.logger.info(f'Attempting to add student: {name} ({student_id}) by user: {session.get("username")}')
        
        db = get_db()
        
        # Check if student already exists
        existing_student = db.execute(
            'SELECT id FROM students WHERE student_id = ?', (student_id,)
        ).fetchone()
        
        if existing_student:
            app.logger.warning(f'Student ID already exists: {student_id}')
            flash('Student ID already exists!', 'error')
            return redirect(url_for('add_student'))
        
        # Handle photo upload
        photo_path = None
        face_encoding = None
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                filename = secure_filename(f"{student_id}_{file.filename}")
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                # Store relative path from static folder
                photo_path = f"student_photos/{filename}"
                app.logger.info(f'Photo uploaded for student {student_id}: {filename}')
                
                # For demo purposes, just mark that face encoding exists
                try:
                    face_encoding = pickle.dumps([1, 2, 3])  # Dummy encoding for demo
                except Exception as e:
                    app.logger.error(f'Error processing photo for student {student_id}: {str(e)}')
                    flash(f'Error processing photo: {str(e)}', 'error')
                    return redirect(url_for('add_student'))
        
        # Create new student with batch
        db.execute(
            'INSERT INTO students (student_id, name, email, batch_id, photo_path, face_encoding) VALUES (?, ?, ?, ?, ?, ?)',
            (student_id, name, email, batch_id if batch_id else None, photo_path, face_encoding)
        )
        db.commit()
        
        # Reload face recognizer
        if face_recognizer:
            face_recognizer.load_known_faces()
        
        app.logger.info(f'Student added successfully: {name} ({student_id})')
        flash('Student added successfully!', 'success')
        
        # Log the action
        log_user_action("CREATE", f"Added student {name} ({student_id})", "STUDENT", student_id)
        
        return redirect(url_for('students'))
    
    # Get batches for the form
    batches = get_student_batches()
    return render_template('add_student.html', batches=batches)

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('students'))
    
    if request.method == 'POST':
        student_id_new = request.form['student_id']
        name = request.form['name']
        email = request.form['email']
        
        # Check if student ID already exists (excluding current student)
        existing_student = db.execute(
            'SELECT id FROM students WHERE student_id = ? AND id != ?', 
            (student_id_new, student_id)
        ).fetchone()
        
        if existing_student:
            flash('Student ID already exists!', 'error')
            return redirect(url_for('edit_student', student_id=student_id))
        
        # Handle photo upload
        photo_path = student['photo_path']  # Keep existing photo by default
        face_encoding = student['face_encoding']  # Keep existing encoding
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                # Delete old photo if it exists
                if student['photo_path']:
                    old_photo_path = os.path.join('static', student['photo_path'])
                    if os.path.exists(old_photo_path):
                        try:
                            os.remove(old_photo_path)
                        except:
                            pass
                
                filename = secure_filename(f"{student_id_new}_{file.filename}")
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                # Store relative path from static folder
                photo_path = f"student_photos/{filename}"
                
                # Generate new face encoding
                try:
                    face_encoding = pickle.dumps([1, 2, 3])  # Dummy encoding for demo
                except Exception as e:
                    flash(f'Error processing photo: {str(e)}', 'error')
                    return redirect(url_for('edit_student', student_id=student_id))
        
        # Update student
        db.execute(
            'UPDATE students SET student_id = ?, name = ?, email = ?, photo_path = ?, face_encoding = ? WHERE id = ?',
            (student_id_new, name, email, photo_path, face_encoding, student_id)
        )
        db.commit()
        
        # Reload face recognizer
        if face_recognizer:
            face_recognizer.load_known_faces()
        
        flash('Student updated successfully!', 'success')
        
        # Log the action
        log_user_action("UPDATE", f"Updated student {name} ({student_id_new})", "STUDENT", student_id_new)
        
        return redirect(url_for('students'))
    
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>')
@admin_required
def delete_student(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('students'))
    
    # Delete photo file if it exists
    if student['photo_path']:
        photo_path = os.path.join('static', student['photo_path'])
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass
            pass
    
    # Delete related records first (due to foreign key constraints)
    db.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
    db.execute('DELETE FROM enrollments WHERE student_id = ?', (student_id,))
    db.execute('DELETE FROM students WHERE id = ?', (student_id,))
    db.commit()
    
    # Reload face recognizer
    if face_recognizer:
        face_recognizer.load_known_faces()
    
    flash(f'Student "{student["name"]}" deleted successfully!', 'success')
    
    # Log the action
    log_user_action("DELETE", f"Deleted student {student['name']} ({student_id})", "STUDENT", student_id)
    
    return redirect(url_for('students'))

@app.route('/courses')
@admin_required
def courses():
    db = get_db()
    # Get course hierarchy
    hierarchy = get_course_hierarchy()
    
    # Also get standalone courses (no hierarchy)
    standalone_courses = db.execute('''
        SELECT * FROM courses 
        WHERE parent_course_id IS NULL AND course_level = 1 AND is_active = 1
        AND id NOT IN (
            SELECT DISTINCT parent_course_id FROM courses 
            WHERE parent_course_id IS NOT NULL
        )
        ORDER BY course_name
    ''').fetchall()
    
    return render_template('courses.html', hierarchy=hierarchy, standalone_courses=standalone_courses)

@app.route('/add_course', methods=['GET', 'POST'])
@admin_required
def add_course():
    if request.method == 'POST':
        course_code = request.form['course_code']
        course_name = request.form['course_name']
        instructor = request.form['instructor']
        schedule = request.form['schedule']
        parent_course_id = request.form.get('parent_course_id')
        min_attendance_percentage = float(request.form.get('min_attendance_percentage', 75.0))
        
        db = get_db()
        
        # Check if course already exists
        existing_course = db.execute(
            'SELECT id FROM courses WHERE course_code = ?', (course_code,)
        ).fetchone()
        
        if existing_course:
            flash('Course code already exists!', 'error')
            return redirect(url_for('add_course'))
        
        # Determine course level
        course_level = 2 if parent_course_id else 1
        
        db.execute(
            '''INSERT INTO courses (course_code, course_name, instructor, schedule, 
                                  parent_course_id, course_level, min_attendance_percentage) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (course_code, course_name, instructor, schedule, 
             parent_course_id if parent_course_id else None, course_level, min_attendance_percentage)
        )
        db.commit()
        
        flash('Course added successfully!', 'success')
        
        # Log the action
        log_user_action("CREATE", f"Added course {course_name} ({course_code})", "COURSE", course_code)
        
        return redirect(url_for('courses'))
    
    # Get main courses for parent selection
    main_courses = get_main_courses()
    return render_template('add_course.html', main_courses=main_courses)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':
        course_code = request.form['course_code']
        course_name = request.form['course_name']
        instructor = request.form['instructor']
        schedule = request.form['schedule']
        parent_course_id = request.form.get('parent_course_id')
        min_attendance_percentage = float(request.form.get('min_attendance_percentage', 75.0))
        
        # Check if course code already exists (excluding current course)
        existing_course = db.execute(
            'SELECT id FROM courses WHERE course_code = ? AND id != ?', 
            (course_code, course_id)
        ).fetchone()
        
        if existing_course:
            flash('Course code already exists!', 'error')
            return redirect(url_for('edit_course', course_id=course_id))
        
        # Determine course level
        course_level = 2 if parent_course_id else 1
        
        # Update course
        db.execute(
            '''UPDATE courses SET course_code = ?, course_name = ?, instructor = ?, 
               schedule = ?, parent_course_id = ?, course_level = ?, min_attendance_percentage = ?
               WHERE id = ?''',
            (course_code, course_name, instructor, schedule, 
             parent_course_id if parent_course_id else None, course_level, 
             min_attendance_percentage, course_id)
        )
        db.commit()
        
        flash('Course updated successfully!', 'success')
        
        # Log the action
        log_user_action("UPDATE", f"Updated course {course_name} ({course_code})", "COURSE", course_id)
        
        return redirect(url_for('courses'))
    
    # Get main courses for parent selection (excluding current course to prevent self-reference)
    main_courses = db.execute(
        'SELECT * FROM courses WHERE course_level = 1 AND is_active = 1 AND id != ? ORDER BY course_name',
        (course_id,)
    ).fetchall()
    
    return render_template('edit_course.html', course=course, main_courses=main_courses)

@app.route('/delete_course/<int:course_id>')
@admin_required
def delete_course(course_id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('courses'))
    
    # Check if this is a main course with sub-courses
    sub_courses = db.execute(
        'SELECT COUNT(*) FROM courses WHERE parent_course_id = ?', (course_id,)
    ).fetchone()[0]
    
    if sub_courses > 0:
        flash('Cannot delete main course that has sub-courses. Delete sub-courses first.', 'error')
        return redirect(url_for('courses'))
    
    # Check if there are any enrollments
    enrollments = db.execute(
        'SELECT COUNT(*) FROM enrollments WHERE course_id = ?', (course_id,)
    ).fetchone()[0]
    
    if enrollments > 0:
        # Instead of hard delete, mark as inactive
        db.execute('UPDATE courses SET is_active = 0 WHERE id = ?', (course_id,))
        db.execute('UPDATE enrollments SET is_active = 0 WHERE course_id = ?', (course_id,))
        flash(f'Course "{course["course_name"]}" has been deactivated (had existing enrollments).', 'warning')
    else:
        # Safe to delete - no enrollments
        db.execute('DELETE FROM batch_course_enrollments WHERE course_id = ?', (course_id,))
        db.execute('DELETE FROM attendance WHERE course_id = ?', (course_id,))
        db.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        flash(f'Course "{course["course_name"]}" deleted successfully!', 'success')
    
    db.commit()
    
    # Log the action
    log_user_action("DELETE", f"Deleted course {course['course_name']} ({course_id})", "COURSE", course_id)
    
    return redirect(url_for('courses'))

# Batch Management Routes
@app.route('/batches')
@admin_required
def batches():
    return render_template('batches.html', batches=get_student_batches())

@app.route('/add_batch', methods=['GET', 'POST'])
@admin_required
def add_batch():
    if request.method == 'POST':
        batch_name = request.form['batch_name']
        batch_year = int(request.form['batch_year'])
        description = request.form.get('description', '')
        min_attendance = float(request.form.get('min_attendance_percentage', 75.0))
        
        db = get_db()
        if db.execute('SELECT id FROM batches WHERE batch_name = ?', (batch_name,)).fetchone():
            flash('Batch name already exists!', 'error')
            return redirect(url_for('add_batch'))
        
        db.execute('''INSERT INTO batches (batch_name, batch_year, description, min_attendance_percentage) 
                     VALUES (?, ?, ?, ?)''', (batch_name, batch_year, description, min_attendance))
        db.commit()
        flash('Batch added successfully!', 'success')
        
        # Log the action
        log_user_action("CREATE", f"Added batch {batch_name}", "BATCH", None)
        
        return redirect(url_for('batches'))
    
    return render_template('add_batch.html')

@app.route('/edit_batch/<int:batch_id>', methods=['GET', 'POST'])
@admin_required
def edit_batch(batch_id):
    db = get_db()
    batch = db.execute('SELECT * FROM batches WHERE id = ?', (batch_id,)).fetchone()
    
    if not batch:
        flash('Batch not found!', 'error')
        return redirect(url_for('batches'))
    
    if request.method == 'POST':
        batch_name = request.form['batch_name']
        batch_year = int(request.form['batch_year'])
        description = request.form.get('description', '')
        min_attendance = float(request.form.get('min_attendance_percentage', 75.0))
        
        # Check if batch name already exists (excluding current batch)
        existing_batch = db.execute(
            'SELECT id FROM batches WHERE batch_name = ? AND id != ?', 
            (batch_name, batch_id)
        ).fetchone()
        
        if existing_batch:
            flash('Batch name already exists!', 'error')
            return redirect(url_for('edit_batch', batch_id=batch_id))
        
        db.execute('''UPDATE batches SET batch_name = ?, batch_year = ?, description = ?, 
                     min_attendance_percentage = ? WHERE id = ?''', 
                  (batch_name, batch_year, description, min_attendance, batch_id))
        db.commit()
        flash('Batch updated successfully!', 'success')
        
        # Log the action
        log_user_action("UPDATE", f"Updated batch {batch_name}", "BATCH", batch_id)
        
        return redirect(url_for('batches'))
    
    return render_template('edit_batch.html', batch=batch)

@app.route('/delete_batch/<int:batch_id>')
@admin_required
def delete_batch(batch_id):
    db = get_db()
    batch = db.execute('SELECT * FROM batches WHERE id = ?', (batch_id,)).fetchone()
    
    if not batch:
        flash('Batch not found!', 'error')
        return redirect(url_for('batches'))
    
    # Check if there are students in this batch
    student_count = db.execute('SELECT COUNT(*) FROM students WHERE batch_id = ?', (batch_id,)).fetchone()[0]
    
    if student_count > 0:
        flash(f'Cannot delete batch "{batch["batch_name"]}" - it has {student_count} students assigned. Reassign students first.', 'error')
        return redirect(url_for('batches'))
    
    # Delete batch course enrollments first
    db.execute('DELETE FROM batch_course_enrollments WHERE batch_id = ?', (batch_id,))
    db.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
    db.commit()
    
    flash(f'Batch "{batch["batch_name"]}" deleted successfully!', 'success')
    
    # Log the action
    log_user_action("DELETE", f"Deleted batch {batch['batch_name']}", "BATCH", batch_id)
    
    return redirect(url_for('batches'))

@app.route('/batch_enrollments/<int:batch_id>')
def batch_enrollments(batch_id):
    db = get_db()
    
    # Get batch details
    batch = db.execute('SELECT * FROM batches WHERE id = ?', (batch_id,)).fetchone()
    if not batch:
        flash('Batch not found!', 'error')
        return redirect(url_for('batches'))
    
    # Get enrolled courses for this batch
    enrolled_courses = db.execute('''
        SELECT c.*, bce.is_mandatory 
        FROM courses c
        JOIN batch_course_enrollments bce ON c.id = bce.course_id
        WHERE bce.batch_id = ?
        ORDER BY c.course_name
    ''', (batch_id,)).fetchall()
    
    # Get available courses (sub-courses only - batches can only be enrolled in sub-courses)
    hierarchy = get_course_hierarchy()
    available_courses = []
    for main_course, sub_courses in hierarchy:
        available_courses.extend(sub_courses)
    
    return render_template('batch_enrollments.html', 
                         batch=batch, 
                         enrolled_courses=enrolled_courses,
                         available_courses=available_courses)

@app.route('/enroll_batch_course', methods=['POST'])
@admin_required
def enroll_batch_course():
    batch_id = int(request.form['batch_id'])
    course_id = int(request.form['course_id'])
    is_mandatory = bool(request.form.get('is_mandatory'))
    
    db = get_db()
    
    # Validate that this is a sub-course (batches can only be enrolled in sub-courses)
    course = db.execute('SELECT parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course or course['parent_course_id'] is None:
        flash('Batches can only be enrolled in sub-courses, not main courses.', 'error')
        return redirect(url_for('batch_enrollments', batch_id=batch_id))
    
    try:
        db.execute(
            '''INSERT OR REPLACE INTO batch_course_enrollments 
               (batch_id, course_id, is_mandatory) VALUES (?, ?, ?)''',
            (batch_id, course_id, is_mandatory)
        )
        db.commit()
        
        flash('Course enrolled for batch successfully!', 'success')
        
        # Log the action
        log_user_action("CREATE", f"Enrolled course in batch: {course_id} -> {batch_id}", "BATCH_COURSE_ENROLLMENT", None)
    except Exception as e:
        flash(f'Error enrolling course: {str(e)}', 'error')
    
    return redirect(url_for('batch_enrollments', batch_id=batch_id))

@app.route('/unenroll_batch_course/<int:batch_id>/<int:course_id>')
@admin_required
def unenroll_batch_course(batch_id, course_id):
    db = get_db()
    
    try:
        db.execute(
            'DELETE FROM batch_course_enrollments WHERE batch_id = ? AND course_id = ?',
            (batch_id, course_id)
        )
        db.commit()
        
        flash('Course unenrolled from batch successfully!', 'success')
        
        # Log the action
        log_user_action("DELETE", f"Unenrolled course from batch: {course_id} -> {batch_id}", "BATCH_COURSE_ENROLLMENT", None)
    except Exception as e:
        flash(f'Error unenrolling course: {str(e)}', 'error')
    
    return redirect(url_for('batch_enrollments', batch_id=batch_id))

@app.route('/enroll')
@admin_required
def enroll():
    """Simple enrollment interface"""
    return redirect(url_for('enrollment_manager'))

@app.route('/bulk_enroll', methods=['POST'])
@admin_required
def bulk_enroll():
    """Bulk enroll students to courses"""
    try:
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        course_ids = data.get('course_ids', [])
        
        if not student_ids or not course_ids:
            return jsonify({'success': False, 'error': 'Please select both students and courses'})
        
        db = get_db()
        added_enrollments = []
        already_enrolled = []
        
        for student_id in student_ids:
            student = db.execute('SELECT name, student_id FROM students WHERE id = ?', (student_id,)).fetchone()
            
            for course_id in course_ids:
                course = db.execute('SELECT course_code, course_name, parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
                
                # Validate that this is a sub-course (students can only enroll in sub-courses)
                if course['parent_course_id'] is None:
                    continue  # Skip main courses
                
                # Check if already enrolled
                existing = db.execute(
                    'SELECT id FROM enrollments WHERE student_id = ? AND course_id = ? AND is_active = 1',
                    (student_id, course_id)
                ).fetchone()
                
                if existing:
                    already_enrolled.append(f"{student['name']} → {course['course_code']}")
                else:
                    enroll_student_with_batch_priority(student_id, course_id)
                    added_enrollments.append(f"{student['name']} → {course['course_code']}")
        
        # Log successful bulk enrollment
        log_user_action("BULK_ENROLL", f"Bulk enrolled {len(added_enrollments)} students in courses", "ENROLLMENT", "")

        return jsonify({
            'success': True,
            'added_enrollments': added_enrollments,
            'already_enrolled': already_enrolled
        })
    
    except Exception as e:
        log_user_action("BULK_ENROLL", f"Failed bulk enrollment", "ENROLLMENT", "", "FAILED")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk_unenroll_students', methods=['POST'])
@admin_required
def bulk_unenroll_students():
    """Bulk unenroll students from courses"""
    try:
        student_ids = request.form.getlist('student_ids')
        course_ids = request.form.getlist('course_ids')
        
        if not student_ids or not course_ids:
            return jsonify({'success': False, 'message': 'Please select both students and courses'})
        
        db = get_db()
        unenrolled_count = 0
        
        for student_id in student_ids:
            for course_id in course_ids:
                result = db.execute(
                    'DELETE FROM enrollments WHERE student_id = ? AND course_id = ?',
                    (int(student_id), int(course_id))
                )
                if result.rowcount > 0:
                    unenrolled_count += 1
        
        db.commit()
        
        # Log successful bulk unenrollment
        log_user_action("BULK_UNENROLL", f"Bulk unenrolled {unenrolled_count} enrollments", "ENROLLMENT", "")
        
        return jsonify({
            'success': True,
            'message': f'Successfully unenrolled {unenrolled_count} enrollments'
        })
    
    except Exception as e:
        log_user_action("BULK_UNENROLL", f"Failed bulk unenrollment", "ENROLLMENT", "", "FAILED")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/toggle_enrollment', methods=['POST'])
@admin_required
def toggle_enrollment():
    """Toggle individual enrollment"""
    try:
        student_id = int(request.form['student_id'])
        course_id = int(request.form['course_id'])
        
        db = get_db()
        
        # Validate that this is a sub-course (students can only enroll in sub-courses)
        course = db.execute('SELECT parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course or course['parent_course_id'] is None:
            return jsonify({'success': False, 'message': 'Students can only be enrolled in sub-courses.'})
        
        # Check if enrollment exists
        existing = db.execute(
            'SELECT id FROM enrollments WHERE student_id = ? AND course_id = ?',
            (student_id, course_id)
        ).fetchone()
        
        if existing:
            # Unenroll
            db.execute('DELETE FROM enrollments WHERE id = ?', (existing['id'],))
            action = 'unenrolled'
            log_user_action("UNENROLL", f"Unenrolled student {student_id} from course {course_id}", "ENROLLMENT", existing['id'])
        else:
            # Enroll
            enroll_student_with_batch_priority(student_id, course_id)
            action = 'enrolled'
            log_user_action("ENROLL", f"Enrolled student {student_id} in course {course_id}", "ENROLLMENT", "")
        
        db.commit()
        
        return jsonify({'success': True, 'action': action})
    
    except Exception as e:
        log_user_action("TOGGLE_ENROLLMENT", f"Failed to toggle enrollment for student {student_id} and course {course_id}", "ENROLLMENT", "", "FAILED")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/settings')
@admin_required
def settings():
    """Settings page"""
    # Log settings page access
    log_user_action("VIEW", "Accessed settings page", "PAGE", "settings")
    
    db = get_db()
    
    # Get current settings or defaults
    general_settings = get_general_settings()
    attendance_settings = get_attendance_settings()
    batch_settings = get_batch_settings()
    system_info = get_system_info()
    
    return render_template('settings.html', 
                         general_settings=general_settings,
                         attendance_settings=attendance_settings,
                         batch_settings=batch_settings,
                         system_info=system_info)

@app.route('/view_system_logs')
@admin_required
def view_system_logs():
    """View system logs page"""
    try:
        # Log access to system logs
        log_user_action("VIEW", "Accessed system logs page", "PAGE", "system_logs")
        
        import os
        log_file_path = 'logs/attendance_system.log'
        logs = []
        
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Get last 100 lines
                logs = lines[-100:] if len(lines) > 100 else lines
                logs.reverse()  # Show newest first
        else:
            logs = ["No log file found. Logging may not be initialized yet."]
        
        # Generate system stats for the template
        db = get_db()
        from datetime import datetime, timedelta
        
        # Count active users (users who logged in within last 24 hours)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        system_stats = {
            'active_users': db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0],
            'recent_attendance': db.execute(
                'SELECT COUNT(*) FROM attendance WHERE created_at > ?', 
                (yesterday,)
            ).fetchone()[0],
            'login_attempts': 0,  # Could be parsed from logs if needed
            'system_errors': 0    # Could be parsed from logs if needed
        }
        
        # Parse logs for additional stats (optional enhancement)
        login_attempts = sum(1 for log in logs if 'Login attempt' in log and yesterday[:10] in log)
        system_errors = sum(1 for log in logs if 'ERROR' in log and yesterday[:10] in log)
        
        system_stats['login_attempts'] = login_attempts
        system_stats['system_errors'] = system_errors
        
        return render_template('system_logs.html', logs=logs, system_stats=system_stats)
        
    except Exception as e:
        app.logger.error(f"Error reading system logs: {str(e)}")
        log_user_action("VIEW", f"Failed to access system logs: {str(e)}", "PAGE", "system_logs", "FAILED")
        flash('Error reading system logs', 'error')
        return redirect(url_for('settings'))

def get_general_settings():
    """Get general system settings"""
    db = get_db()
    settings = db.execute('SELECT * FROM system_settings WHERE category = "general"').fetchall()
    
    result = {
        'institution_name': 'Your Institution',
        'academic_year': '2024-2025',
        'current_semester': 'Fall',
        'default_attendance_threshold': 75.0,
        'institution_logo': ''
    }
    
    for setting in settings:
        result[setting['setting_key']] = setting['setting_value']
    
    return result

def get_attendance_settings():
    """Get attendance configuration settings"""
    db = get_db()
    settings = db.execute('SELECT * FROM system_settings WHERE category = "attendance"').fetchall()
    
    result = {
        'grace_period_minutes': 10,
        'calculation_method': 'percentage',
        'auto_aggregate_main_courses': True,
        'low_attendance_threshold': 50.0
    }
    
    for setting in settings:
        if setting['setting_key'] in ['grace_period_minutes', 'low_attendance_threshold']:
            result[setting['setting_key']] = float(setting['setting_value'])
        elif setting['setting_key'] == 'auto_aggregate_main_courses':
            result[setting['setting_key']] = setting['setting_value'].lower() == 'true'
        else:
            result[setting['setting_key']] = setting['setting_value']
    
    return result

def get_batch_settings():
    """Get batch management settings"""
    db = get_db()
    settings = db.execute('SELECT * FROM system_settings WHERE category = "batch"').fetchall()
    
    result = {
        'naming_convention': 'year_only',
        'auto_create_batches': False,
        'promotion_threshold': 75.0
    }
    
    for setting in settings:
        if setting['setting_key'] == 'promotion_threshold':
            result[setting['setting_key']] = float(setting['setting_value'])
        elif setting['setting_key'] == 'auto_create_batches':
            result[setting['setting_key']] = setting['setting_value'].lower() == 'true'
        else:
            result[setting['setting_key']] = setting['setting_value']
    
    return result

def get_system_info():
    """Get system information"""
    db = get_db()
    
    # Get database size
    db_size = "Unknown"
    try:
        import os
        db_size = f"{os.path.getsize(app.config['DATABASE']) / (1024*1024):.1f} MB"
    except:
        pass
    
    # Get counts
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_courses = db.execute('SELECT COUNT(*) FROM courses WHERE is_active = 1').fetchone()[0]
    
    # Get last backup info
    last_backup = db.execute(
        'SELECT setting_value FROM system_settings WHERE category = "system" AND setting_key = "last_backup"'
    ).fetchone()
    
    return {
        'db_size': db_size,
        'total_students': total_students,
        'total_courses': total_courses,
        'last_backup': last_backup[0] if last_backup else 'Never'
    }

@app.route('/update_general_settings', methods=['POST'])
@admin_required
def update_general_settings():
    """Update general system settings"""
    db = get_db()
    
    # Handle logo upload
    logo_filename = None
    if 'institution_logo' in request.files:
        file = request.files['institution_logo']
        if file and file.filename != '':
            # Create logos directory if it doesn't exist
            logo_dir = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'logos')
            os.makedirs(logo_dir, exist_ok=True)
            
            # Save the file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            logo_filename = f"logo_{timestamp}_{filename}"
            file.save(os.path.join(logo_dir, logo_filename))
    
    settings = {
        'institution_name': request.form.get('institution_name'),
        'academic_year': request.form.get('academic_year'),
        'current_semester': request.form.get('current_semester'),
        'default_attendance_threshold': request.form.get('default_attendance_threshold')
    }
    
    if logo_filename:
        settings['institution_logo'] = logo_filename
    
    for key, value in settings.items():
        if value is not None:
            db.execute('''
                INSERT OR REPLACE INTO system_settings (category, setting_key, setting_value)
                VALUES ('general', ?, ?)
            ''', (key, value))
    
    db.commit()
    
    # Log settings update
    log_user_action("UPDATE", f"Updated general settings", "SETTINGS", "general")
    
    flash('General settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_attendance_settings', methods=['POST'])
@admin_required
def update_attendance_settings():
    """Update attendance configuration settings"""
    db = get_db()
    
    settings = {
        'grace_period_minutes': request.form.get('grace_period_minutes'),
        'calculation_method': request.form.get('attendance_calculation_method'),
        'auto_aggregate_main_courses': 'true' if request.form.get('auto_aggregate_main_courses') else 'false',
        'low_attendance_threshold': request.form.get('low_attendance_threshold')
    }
    
    for key, value in settings.items():
        if value is not None:
            db.execute('''
                INSERT OR REPLACE INTO system_settings (category, setting_key, setting_value)
                VALUES ('attendance', ?, ?)
            ''', (key, value))
    
    db.commit()
    
    # Log settings update
    log_user_action("UPDATE", f"Updated attendance settings", "SETTINGS", "attendance")
    
    flash('Attendance settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_batch_settings', methods=['POST'])
@admin_required
def update_batch_settings():
    """Update batch management settings"""
    db = get_db()
    
    settings = {
        'naming_convention': request.form.get('batch_naming_convention'),
        'auto_create_batches': 'true' if request.form.get('auto_create_batches') else 'false',
        'promotion_threshold': request.form.get('batch_promotion_threshold'),
        'custom_pattern': request.form.get('custom_pattern', '')
    }
    
    for key, value in settings.items():
        if value is not None:
            db.execute('''
                INSERT OR REPLACE INTO system_settings (category, setting_key, setting_value)
                VALUES ('batch', ?, ?)
            ''', (key, value))
    
    db.commit()
    flash('Batch settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/backup_database')
@admin_required
def backup_database():
    """Create and download database backup"""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"attendance_backup_{timestamp}.db"
        backup_path = os.path.join(app.root_path, 'backups', backup_filename)
        
        # Create backups directory if it doesn't exist
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copy database file
        shutil.copy2(app.config['DATABASE'], backup_path)
        
        # Update last backup timestamp
        db = get_db()
        db.execute('''
            INSERT OR REPLACE INTO system_settings (category, setting_key, setting_value)
            VALUES ('system', 'last_backup', ?)
        ''', (datetime.now().isoformat(),))
        db.commit()
        
        # Log backup creation
        log_user_action("BACKUP", f"Created database backup: {backup_filename}", "DATABASE", backup_filename)
        
        # Return file for download
        from flask import send_file
        return send_file(backup_path, as_attachment=True, download_name=backup_filename)
        
    except Exception as e:
        log_user_action("BACKUP", f"Failed to create database backup: {str(e)}", "DATABASE", "", "FAILED")
        flash(f'Backup failed: {str(e)}', 'error')
        return redirect(url_for('settings'))

@app.route('/restore_database', methods=['POST'])
@admin_required
def restore_database():
    """Restore database from backup"""
    try:
        if 'backup_file' not in request.files:
            flash('No backup file selected!', 'error')
            return redirect(url_for('settings'))
        
        file = request.files['backup_file']
        if file.filename == '':
            flash('No backup file selected!', 'error')
            return redirect(url_for('settings'))
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Validate the backup file (basic check)
        import sqlite3
        test_conn = sqlite3.connect(temp_path)
        test_conn.execute('SELECT COUNT(*) FROM sqlite_master')
        test_conn.close()
        
        # Close current connection
        if hasattr(g, '_database'):
            g._database.close()
            g._database = None
        
        # Replace current database
        import shutil
        shutil.move(temp_path, app.config['DATABASE'])
        
        # Log database restore
        log_user_action("RESTORE", f"Restored database from backup file: {file.filename}", "DATABASE", file.filename)
        
        flash('Database restored successfully!', 'success')
        
    except Exception as e:
        log_user_action("RESTORE", f"Failed to restore database from backup: {str(e)}", "DATABASE", "", "FAILED")
        flash(f'Restore failed: {str(e)}', 'error')
        
    return redirect(url_for('settings'))

@app.route('/cleanup_old_data', methods=['POST'])
@admin_required
def cleanup_old_data():
    """Clean up old attendance data"""
    try:
        data = request.get_json()
        months = int(data.get('months', 12))
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        db = get_db()
        result = db.execute(
            'DELETE FROM attendance WHERE created_at < ?',
            (cutoff_date.isoformat(),)
        )
        
        deleted_count = result.rowcount
        db.commit()
        
        # Log cleanup operation
        log_user_action("CLEANUP", f"Cleaned up {deleted_count} attendance records older than {months} months", "MAINTENANCE", "")
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} old attendance records'
        })
        
    except Exception as e:
        log_user_action("CLEANUP", f"Failed to cleanup old data: {str(e)}", "MAINTENANCE", "", "FAILED")
        return jsonify({
            'success': False,
            'message': str(e)
        })

# API Routes for Statistics
@app.route('/api/stats')
@attendance_taker_required
def api_stats():
    """API endpoint for dashboard statistics"""
    db = get_db()
    
    # Total students
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    
    # Total sub-courses (where students are enrolled)
    total_courses = db.execute('SELECT COUNT(*) FROM courses WHERE parent_course_id IS NOT NULL').fetchone()[0]
    
    # Today's attendance
    today = date.today().isoformat()
    today_attendance = db.execute('''
        SELECT COUNT(DISTINCT student_id) 
        FROM attendance 
        WHERE date = ? AND status = 'Present'
    ''', (today,)).fetchone()[0]
    
    return jsonify({
        'total_students': total_students,
        'total_courses': total_courses,
        'today_attendance': today_attendance
    })

# API Routes for Session Management
@app.route('/api/update-activity', methods=['POST'])
@login_required
def api_update_activity():
    """API endpoint to update user activity timestamp"""
    session['last_activity'] = datetime.now().isoformat()
    return jsonify({'status': 'success', 'timestamp': session['last_activity']})

@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    general_settings = get_general_settings()
    return dict(
        institution_name=general_settings.get('institution_name', 'Your Institution'),
        institution_logo=general_settings.get('institution_logo', ''),
        current_year=datetime.now().year,
        current_semester=general_settings.get('current_semester', 'Fall'),
        academic_year=general_settings.get('academic_year', '2024-2025')
    )

@app.route('/enrollment_manager')
@admin_required
def enrollment_manager():
    """Advanced enrollment management with matrix view"""
    db = get_db()
    
    # Get all students with their batch info
    students = db.execute('''
        SELECT s.id, s.student_id, s.name, s.email, b.batch_name 
        FROM students s 
        LEFT JOIN batches b ON s.batch_id = b.id 
        ORDER BY s.name
    ''').fetchall()
    
    # Get all sub-courses (where students can be enrolled)
    hierarchy = get_course_hierarchy()
    sub_courses = []
    for main_course, sub_course_list in hierarchy:
        sub_courses.extend(sub_course_list)
    
    # Get all current enrollments
    enrollments = db.execute('''
        SELECT student_id, course_id, enrollment_type 
        FROM enrollments 
        WHERE is_active = 1
    ''').fetchall()
    
    # Create enrollment matrix
    enrollment_matrix = {}
    for enrollment in enrollments:
        key = f"{enrollment['student_id']}-{enrollment['course_id']}"
        enrollment_matrix[key] = enrollment['enrollment_type']
    
    return render_template('enrollment_manager.html', 
                         students=students, 
                         courses=sub_courses,
                         sub_courses=sub_courses,
                         enrollment_matrix=enrollment_matrix)

@app.route('/mark_attendance', methods=['GET', 'POST'])
@attendance_taker_required
def mark_attendance():
    """Mark attendance page with multiple options"""
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        if course_id:
            # Redirect to webcam attendance with selected course
            return redirect(url_for('webcam_attendance', course_id=course_id))
        else:
            flash('Please select a course before starting face recognition.', 'error')
    
    hierarchy = get_course_hierarchy()
    return render_template('mark_attendance.html', hierarchy=hierarchy)

@app.route('/webcam_attendance')
@attendance_taker_required
def webcam_attendance():
    """Webcam-based attendance marking"""
    course_id = request.args.get('course_id')
    if not course_id:
        app.logger.warning('Webcam attendance accessed without course_id')
        flash('Please select a course for attendance marking.', 'error')
        return redirect(url_for('mark_attendance'))
    
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        app.logger.warning(f'Webcam attendance: Course not found (ID: {course_id})')
        flash('Course not found!', 'error')
        return redirect(url_for('mark_attendance'))
    
    app.logger.info(f'Webcam attendance started for course: {course["course_name"]} (ID: {course_id}) by user: {session.get("username")}')
    return render_template('webcam_attendance.html', course=course)

@app.route('/manual_attendance/<int:course_id>')
@attendance_taker_required
def manual_attendance(course_id):
    """Manual attendance marking for a specific course"""
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('mark_attendance'))
    
    # Get enrolled students for this course
    students = db.execute('''
        SELECT s.*, b.batch_name 
        FROM students s 
        LEFT JOIN batches b ON s.batch_id = b.id
        JOIN enrollments e ON s.id = e.student_id 
        WHERE e.course_id = ? AND e.is_active = 1
        ORDER BY s.name
    ''', (course_id,)).fetchall()
    
    return render_template('manual_attendance.html', course=course, students=students)

@app.route('/quick_checkin/<int:course_id>')
@attendance_taker_required
def quick_checkin(course_id):
    """Quick check-in interface for a course"""
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('mark_attendance'))
    
    return render_template('quick_checkin.html', course=course)

@app.route('/quick_checkin_submit', methods=['POST'])
@attendance_taker_required
def quick_checkin_submit():
    """Submit quick check-in attendance"""
    try:
        course_id = request.form.get('course_id')
        student_id = request.form.get('student_id')
        
        if not course_id or not student_id:
            return jsonify({
                'success': False, 
                'message': 'Missing course or student information!'
            })
        
        from datetime import datetime
        now = datetime.now()
        
        # Get student info for logging
        db = get_db()
        student = db.execute('SELECT name, student_id FROM students WHERE id = ?', (student_id,)).fetchone()
        course = db.execute('SELECT course_name FROM courses WHERE id = ?', (course_id,)).fetchone()
        
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found!'
            })
        
        if not course:
            return jsonify({
                'success': False,
                'message': 'Course not found!'
            })
        
        # Check if already marked today
        today = now.date().isoformat()
        existing = db.execute(
            'SELECT id FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?',
            (student_id, course_id, today)
        ).fetchone()
        
        if existing:
            return jsonify({
                'success': False,
                'message': f'{student["name"]} attendance already marked for today!'
            })
        
        # Mark attendance
        mark_attendance_with_aggregation(
            student_id=int(student_id),
            course_id=int(course_id),
            date=now.date(),
            time=now.time().strftime('%H:%M:%S'),
            status='Present'
        )
        
        # Log quick checkin
        log_user_action("QUICK_CHECKIN", f"Quick checkin for {student['name']} ({student['student_id']}) in {course['course_name']}", "ATTENDANCE", student_id)
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked successfully for {student["name"]}!'
        })
        
    except Exception as e:
        log_user_action("QUICK_CHECKIN", f"Failed quick checkin for student {student_id} in course {course_id}: {str(e)}", "ATTENDANCE", student_id, "FAILED")
        return jsonify({
            'success': False,
            'message': f'Error marking attendance: {str(e)}'
        })

@app.route('/bulk_attendance/<int:course_id>')
@attendance_taker_required
def bulk_attendance(course_id):
    """Bulk attendance marking for a course"""
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('mark_attendance'))
    
    # Get enrolled students for this course
    students = db.execute('''
        SELECT s.*, b.batch_name 
        FROM students s 
        LEFT JOIN batches b ON s.batch_id = b.id
        JOIN enrollments e ON s.id = e.student_id 
        WHERE e.course_id = ? AND e.is_active = 1
        ORDER BY s.name
    ''', (course_id,)).fetchall()
    
    return render_template('bulk_attendance.html', course=course, students=students)

@app.route('/save_bulk_attendance', methods=['POST'])
@attendance_taker_required
def save_bulk_attendance():
    """Save bulk attendance data"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        attendance_data = data.get('attendance_data', {})
        
        if not course_id or not attendance_data:
            return jsonify({
                'success': False,
                'message': 'Missing course or attendance data'
            })
        
        db = get_db()
        from datetime import datetime
        now = datetime.now()
        today = now.date().isoformat()
        now_time = now.time().strftime('%H:%M:%S')
        
        # Get course info
        course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({
                'success': False,
                'message': 'Course not found'
            })
        
        processed_students = []
        
        # Process each student's attendance
        for student_id, status in attendance_data.items():
            if not student_id or not status:
                continue
            
            # Get student info
            student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
            if not student:
                continue
            
            # Check if already marked today
            existing = db.execute(
                'SELECT id FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?',
                (student_id, course_id, today)
            ).fetchone()
            
            if not existing:
                # Mark attendance using the main function to handle aggregation
                mark_attendance_with_aggregation(
                    student_id=int(student_id),
                    course_id=int(course_id),
                    date=now.date(),
                    time=now_time,
                    status=status.capitalize()
                )
                
                # Add to processed list if present
                if status.lower() == 'present':
                    processed_students.append(student['name'])
        
        # Log bulk attendance
        log_user_action("BULK_ATTENDANCE", f"Bulk attendance saved for {len(attendance_data)} students in course {course_id}", "ATTENDANCE", course_id)
        
        return jsonify({
            'success': True,
            'message': f'Attendance saved successfully for {len(attendance_data)} students',
            'processed_students': processed_students
        })
    
    except Exception as e:
        log_user_action("BULK_ATTENDANCE", f"Failed to save bulk attendance for course {course_id}: {str(e)}", "ATTENDANCE", course_id, "FAILED")
        return jsonify({
            'success': False,
            'message': f'Error saving attendance: {str(e)}'
        })

@app.route('/manual_attendance_submit', methods=['POST'])
@attendance_taker_required
def manual_attendance_submit():
    """Submit manual attendance data"""
    try:
        course_id = request.form.get('course_id')
        students = request.form.get('students')
        date = request.form.get('date')
        time = request.form.get('time')
        
        if not course_id or not students:
            return jsonify({'success': False, 'error': 'Missing course or student data'})
        
        # Parse student IDs
        student_ids = [int(sid.strip()) for sid in students.split(',') if sid.strip()]
        
        if not student_ids:
            return jsonify({'success': False, 'error': 'No students selected'})
        
        db = get_db()
        marked_students = []
        already_marked = []
        
        # Get course info
        course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'success': False, 'error': 'Course not found'})
        
        # Mark attendance for each student
        for student_id in student_ids:
            # Get student info
            student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
            if not student:
                continue
            
            # Check if already marked today
            existing = db.execute(
                'SELECT id FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?',
                (student_id, course_id, date)
            ).fetchone()
            
            if not existing:
                # Mark attendance
                db.execute(
                    'INSERT INTO attendance (student_id, course_id, date, time, status) VALUES (?, ?, ?, ?, ?)',
                    (student_id, course_id, date, time, 'Present')
                )
                marked_students.append(student['name'])
            else:
                already_marked.append(student['name'])
        
        db.commit()
        
        # Log attendance submission
        log_user_action("MARK_ATTENDANCE", f"Manual attendance marked for {len(marked_students)} students in course {course_id}", "ATTENDANCE", course_id)
        
        return jsonify({
            'success': True,
            'message': f'Attendance saved successfully for {len(marked_students)} students',
            'marked_students': marked_students,
            'already_marked': already_marked
        })
    
    except Exception as e:
        log_user_action("MARK_ATTENDANCE", f"Failed to mark manual attendance for course {course_id}", "ATTENDANCE", course_id, "FAILED")
        return jsonify({'success': False, 'error': str(e)})

# Face Recognition API Endpoints

@app.route('/api/recognize_faces', methods=['POST'])
@attendance_taker_required
def api_recognize_faces():
    """API endpoint to recognize faces from webcam frame"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image data provided'})
        
        # Decode base64 image
        image_data = data['image'].split(',')[1]  # Remove data:image/jpeg;base64, part
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'error': 'Invalid image data'})
        
        # Initialize face recognizer if not already done
        global face_recognizer
        if face_recognizer is None:
            init_face_recognizer()
        
        # Recognize faces
        recognized_students, face_locations = face_recognizer.recognize_faces(frame)
        
        app.logger.info(f"Face recognition API: Found {len(recognized_students)} recognized students")
        
        return jsonify({
            'success': True,
            'recognized_students': recognized_students,
            'face_count': len(face_locations)
        })
        
    except Exception as e:
        app.logger.error(f"Face recognition API error: {str(e)}")
        return jsonify({'success': False, 'error': f'Recognition failed: {str(e)}'})

@app.route('/api/mark_webcam_attendance', methods=['POST'])
@attendance_taker_required
def api_mark_webcam_attendance():
    """API endpoint to mark attendance for recognized faces"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        student_ids = data.get('student_ids', [])
        
        if not course_id:
            return jsonify({'success': False, 'error': 'Course ID is required'})
        
        if not student_ids:
            return jsonify({'success': False, 'error': 'No students to mark attendance for'})
        
        db = get_db()
        from datetime import datetime
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.time().strftime('%H:%M:%S')
        
        # Get course info
        course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'success': False, 'error': 'Course not found'})
        
        marked_students = []
        already_marked = []
        
        for student_id in student_ids:
            # Get student info
            student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
            if not student:
                continue
                
            # Check if already marked today
            existing = db.execute(
                'SELECT id FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?',
                (student_id, course_id, today)
            ).fetchone()
            
            if not existing:
                # Mark attendance using the aggregation function
                mark_attendance_with_aggregation(
                    student_id=student_id,
                    course_id=int(course_id),
                    date=now.date(),
                    time=current_time,
                    status='Present'
                )
                marked_students.append({
                    'id': student['id'],
                    'name': student['name'],
                    'student_id': student['student_id']
                })
                app.logger.info(f"Webcam attendance marked for: {student['name']} ({student['student_id']})")
            else:
                already_marked.append({
                    'id': student['id'], 
                    'name': student['name'],
                    'student_id': student['student_id']
                })
        
        # Log webcam attendance
        log_user_action("WEBCAM_ATTENDANCE", f"Webcam attendance marked for {len(marked_students)} students in course {course_id}", "ATTENDANCE", course_id)
        
        return jsonify({
            'success': True,
            'marked_students': marked_students,
            'already_marked': already_marked,
            'message': f'Successfully marked attendance for {len(marked_students)} students'
        })
        
    except Exception as e:
        app.logger.error(f"Webcam attendance marking error: {str(e)}")
        log_user_action("WEBCAM_ATTENDANCE", f"Failed webcam attendance for course {course_id}: {str(e)}", "ATTENDANCE", course_id, "FAILED")
        return jsonify({'success': False, 'error': f'Failed to mark attendance: {str(e)}'})

@app.route('/users')
@admin_required
def users():
    """User management page"""
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add new user"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        full_name = request.form['full_name']
        email = request.form.get('email', '')
        
        db = get_db()
        
        # Check if username already exists
        existing_user = db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            flash('Username already exists!', 'error')
            return redirect(url_for('add_user'))
        
        # Hash password and create user
        password_hash = hash_password(password)
        db.execute(
            '''INSERT INTO users (username, password_hash, role, full_name, email, is_active) 
               VALUES (?, ?, ?, ?, ?, 1)''',
            (username, password_hash, role, full_name, email)
        )
        db.commit()
        
        # Log user creation
        log_user_action("CREATE", f"Added user {username} ({full_name}) with role {role}", "USER", username)
        
        flash('User added successfully!', 'success')
        return redirect(url_for('users'))
    
    return render_template('add_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user"""
    db = get_db()
    
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        full_name = request.form['full_name']
        email = request.form.get('email', '')
        is_active = 1 if request.form.get('is_active') else 0
        
        # Check if username already exists (excluding current user)
        existing = db.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id)).fetchone()
        if existing:
            flash('Username already exists!', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Update user
        db.execute('''UPDATE users SET username = ?, role = ?, full_name = ?, email = ?, is_active = ?, 
                     updated_at = CURRENT_TIMESTAMP WHERE id = ?''',
                  (username, role, full_name, email, is_active, user_id))
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            password_hash = hash_password(new_password)
            db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        
        db.commit()
        
        # Log user update
        log_user_action("UPDATE", f"Updated user {username} ({full_name}) with role {role}", "USER", str(user_id))
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('users'))
    
    # GET request - show edit form
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('users'))
    
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    db = get_db()
    
    # Check if user exists and is not the current user
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('users'))
    
    if user['id'] == session.get('user_id'):
        flash('You cannot delete yourself!', 'error')
        return redirect(url_for('users'))
    
    # Delete user
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    
    # Log user deletion
    log_user_action("DELETE", f"Deleted user {user['username']} ({user['full_name']})", "USER", str(user_id))
    
    flash(f'User "{user["username"]}" deleted successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/generate_report')
@attendance_taker_required
def generate_report():
    """Generate attendance report based on filters"""
    db = get_db()
    
    # Get filter parameters
    course_id = request.args.get('course_id')
    batch_id = request.args.get('batch_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build the query dynamically based on filters
    where_conditions = []
    query_params = []
    
    base_query = '''
        SELECT s.student_id, s.name, c.course_code, c.course_name, 
               a.date, a.time, a.status, b.batch_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN courses c ON a.course_id = c.id
        LEFT JOIN batches b ON s.batch_id = b.id
    '''
    
    if course_id:
        where_conditions.append('a.course_id = ?')
        query_params.append(course_id)
    
    if batch_id:
        where_conditions.append('s.batch_id = ?')
        query_params.append(batch_id)
    
    if date_from:
        where_conditions.append('a.date >= ?')
        query_params.append(date_from)
    
    if date_to:
        where_conditions.append('a.date <= ?')
        query_params.append(date_to)
    
    if where_conditions:
        base_query += ' WHERE ' + ' AND '.join(where_conditions)
    
    base_query += ' ORDER BY a.date DESC, s.name'
    
    # Execute query
    attendance_records = db.execute(base_query, query_params).fetchall()
    
    # Get summary statistics
    summary = {}
    if attendance_records:
        total_records = len(attendance_records)
        present_records = len([r for r in attendance_records if r['status'] == 'Present'])
        summary = {
            'total_records': total_records,
            'present_records': present_records,
            'absent_records': total_records - present_records,
            'attendance_rate': round((present_records / total_records) * 100, 2) if total_records > 0 else 0
        }
    
    # Get data for dropdowns
    courses = db.execute('SELECT id, course_code, course_name FROM courses WHERE is_active = 1 ORDER BY course_name').fetchall()
    batches = db.execute('SELECT id, batch_name FROM batches ORDER BY batch_name').fetchall()
    
    # Get selected course information if course_id is provided
    selected_course = None
    if course_id:
        selected_course = db.execute('SELECT id, course_code, course_name FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    return render_template('attendance_report.html', 
                         attendance_records=attendance_records,
                         attendance_data=attendance_records,
                         summary=summary,
                         courses=courses,
                         batches=batches,
                         selected_course=selected_course,
                         filters={
                             'course_id': course_id,
                             'batch_id': batch_id,
                             'date_from': date_from,
                             'date_to': date_to
                         })

@app.route('/bulk_upload', methods=['GET', 'POST'])
@admin_required
def bulk_upload():
    """Bulk upload students, courses, and enrollments from CSV files"""
    if request.method == 'POST':
        # Handle file upload logic here
        flash('Bulk upload functionality coming soon!', 'info')
        return redirect(url_for('bulk_upload'))
    
    return render_template('bulk_upload.html')

@app.route('/bulk_upload_students', methods=['POST'])
@admin_required
def bulk_upload_students():
    """Handle bulk upload of students from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'})
        
        # Read CSV file
        import csv
        import io
        
        # Read file content
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Validate CSV headers
        required_headers = ['student_id', 'name', 'email']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({
                'success': False, 
                'error': f'CSV must have headers: {", ".join(required_headers)}'
            })
        
        db = get_db()
        added_students = []
        skipped_students = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                student_id = row['student_id'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                batch_id = row.get('batch_id', '').strip() if row.get('batch_id') else None
                
                if not student_id or not name or not email:
                    errors.append(f'Row {row_num}: Missing required fields')
                    continue
                
                # Check if student already exists
                existing = db.execute(
                    'SELECT id FROM students WHERE student_id = ? OR email = ?',
                    (student_id, email)
                ).fetchone()
                
                if existing:
                    skipped_students.append(f'{name} ({student_id})')
                    continue
                
                # Insert student
                db.execute(
                    '''INSERT INTO students (student_id, name, email, batch_id)
                       VALUES (?, ?, ?, ?)''',
                    (student_id, name, email, batch_id)
                )
                
                added_students.append(f'{name} ({student_id})')
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(added_students)} students',
            'details': {
                'added': added_students,
                'skipped': skipped_students,
                'errors': errors
            }
        })
        
    except Exception as e:
        app.logger.error(f'Error in bulk_upload_students: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk_upload_courses', methods=['POST'])
@admin_required
def bulk_upload_courses():
    """Handle bulk upload of courses from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'})
        
        # Read CSV file
        import csv
        import io
        
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Validate CSV headers
        required_headers = ['course_code', 'course_name', 'instructor']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({
                'success': False, 
                'error': f'CSV must have headers: {", ".join(required_headers)}'
            })
        
        db = get_db()
        added_courses = []
        skipped_courses = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                course_code = row['course_code'].strip()
                course_name = row['course_name'].strip()
                instructor = row['instructor'].strip()
                schedule = row.get('schedule', '').strip()
                parent_course_id = row.get('parent_course_id', '').strip()
                min_attendance = row.get('min_attendance_percentage', '75.0').strip()
                
                if not course_code or not course_name or not instructor:
                    errors.append(f'Row {row_num}: Missing required fields')
                    continue
                
                # Check if course already exists
                existing = db.execute(
                    'SELECT id FROM courses WHERE course_code = ?',
                    (course_code,)
                ).fetchone()
                
                if existing:
                    skipped_courses.append(f'{course_name} ({course_code})')
                    continue
                
                # Determine course level
                course_level = 2 if parent_course_id else 1
                parent_id = int(parent_course_id) if parent_course_id else None
                
                # Insert course
                db.execute(
                    '''INSERT INTO courses (course_code, course_name, instructor, schedule, 
                                          parent_course_id, course_level, min_attendance_percentage)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (course_code, course_name, instructor, schedule, parent_id, course_level, float(min_attendance))
                )
                
                added_courses.append(f'{course_name} ({course_code})')
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(added_courses)} courses',
            'details': {
                'added': added_courses,
                'skipped': skipped_courses,
                'errors': errors
            }
        })
        
    except Exception as e:
        app.logger.error(f'Error in bulk_upload_courses: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk_upload_enrollments', methods=['POST'])
@admin_required
def bulk_upload_enrollments():
    """Handle bulk upload of enrollments from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'})
        
        # Read CSV file
        import csv
        import io
        
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Validate CSV headers
        required_headers = ['student_id', 'course_code']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({
                'success': False, 
                'error': f'CSV must have headers: {", ".join(required_headers)}'
            })
        
        db = get_db()
        added_enrollments = []
        skipped_enrollments = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                student_id = row['student_id'].strip()
                course_code = row['course_code'].strip()
                
                if not student_id or not course_code:
                    errors.append(f'Row {row_num}: Missing required fields')
                    continue
                
                # Get student ID from student_id
                student = db.execute(
                    'SELECT id FROM students WHERE student_id = ?',
                    (student_id,)
                ).fetchone()
                
                if not student:
                    errors.append(f'Row {row_num}: Student {student_id} not found')
                    continue
                
                # Get course ID from course_code
                course = db.execute(
                    'SELECT id, parent_course_id FROM courses WHERE course_code = ?',
                    (course_code,)
                ).fetchone()
                
                if not course:
                    errors.append(f'Row {row_num}: Course {course_code} not found')
                    continue
                
                # Check if this is a sub-course (students can only enroll in sub-courses)
                if not course['parent_course_id']:
                    errors.append(f'Row {row_num}: Students can only enroll in sub-courses, not main courses')
                    continue
                
                # Check if enrollment already exists
                existing = db.execute(
                    'SELECT id FROM enrollments WHERE student_id = ? AND course_id = ?',
                    (student['id'], course['id'])
                ).fetchone()
                
                if existing:
                    skipped_enrollments.append(f'{student_id} -> {course_code}')
                    continue
                
                # Create enrollment
                db.execute(
                    '''INSERT INTO enrollments (student_id, course_id, enrollment_type, is_active)
                       VALUES (?, ?, 'direct', 1)''',
                    (student['id'], course['id'])
                )
                
                added_enrollments.append(f'{student_id} -> {course_code}')
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(added_enrollments)} enrollments',
            'details': {
                'added': added_enrollments,
                'skipped': skipped_enrollments,
                'errors': errors
            }
        })
        
    except Exception as e:
        app.logger.error(f'Error in bulk_upload_enrollments: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk_upload_courses_validate', methods=['POST'])
@admin_required
def bulk_upload_courses_validate():
    """Validate bulk upload of courses without saving"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'})
        
        import csv, io
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        required_headers = ['course_code', 'course_name', 'instructor']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({'success': False, 'error': f'CSV must have headers: {", ".join(required_headers)}'})
        
        db = get_db()
        validated_courses = []
        skipped_courses = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                course_code = row['course_code'].strip()
                course_name = row['course_name'].strip()
                instructor = row['instructor'].strip()
                
                if not course_code or not course_name or not instructor:
                    errors.append(f'Row {row_num}: Missing required fields')
                    continue
                
                existing = db.execute('SELECT id FROM courses WHERE course_code = ?', (course_code,)).fetchone()
                if existing:
                    skipped_courses.append(f'{course_name} ({course_code})')
                    continue
                
                validated_courses.append({
                    'course_code': course_code,
                    'course_name': course_name,
                    'instructor': instructor,
                    'schedule': row.get('schedule', '').strip(),
                    'parent_course_id': int(row.get('parent_course_id', '')) if row.get('parent_course_id', '').strip() else None,
                    'min_attendance_percentage': float(row.get('min_attendance_percentage', '75.0'))
                })
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        return jsonify({
            'success': True,
            'courses': validated_courses,
            'details': {
                'added': [f"{c['course_name']} ({c['course_code']})" for c in validated_courses],
                'skipped': skipped_courses,
                'errors': errors
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk_upload_students_validate', methods=['POST'])
@admin_required
def bulk_upload_students_validate():
    """Validate bulk upload of students without saving"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'})
        
        import csv, io
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        required_headers = ['student_id', 'name', 'email']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({'success': False, 'error': f'CSV must have headers: {", ".join(required_headers)}'})
        
        db = get_db()
        validated_students = []
        skipped_students = []
        errors = []
        batch_names = set()
        existing_batches = set()
        
        # Get existing batch names
        existing_batch_records = db.execute('SELECT batch_name FROM batches').fetchall()
        existing_batch_names = {batch['batch_name'] for batch in existing_batch_records}
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                student_id = row['student_id'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                batch_name = row.get('batch_name', '').strip() if 'batch_name' in row else None
                
                app.logger.info(f"Processing row {row_num}: student_id={student_id}, batch_name='{batch_name}'")
                
                if not student_id or not name or not email:
                    errors.append(f'Row {row_num}: Missing required fields')
                    continue
                
                existing = db.execute('SELECT id FROM students WHERE student_id = ? OR email = ?', (student_id, email)).fetchone()
                if existing:
                    skipped_students.append(f'{name} ({student_id})')
                    continue
                
                # Track batch names
                if batch_name:
                    batch_names.add(batch_name)
                    if batch_name in existing_batch_names:
                        existing_batches.add(batch_name)
                
                validated_students.append({
                    'student_id': student_id,
                    'name': name,
                    'email': email,
                    'batch_name': batch_name
                })
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        # Determine new batches to create
        new_batches = batch_names - existing_batches
        
        return jsonify({
            'success': True,
            'students': validated_students,
            'batch_summary': {
                'new_batches': list(new_batches),
                'existing_batches': list(existing_batches)
            },
            'details': {
                'added': [f"{s['name']} ({s['student_id']})" for s in validated_students],
                'skipped': skipped_students,
                'errors': errors
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finalize_bulk_upload', methods=['POST'])
@admin_required 
def finalize_bulk_upload():
    """Finalize bulk upload - all or nothing"""
    try:
        data = request.get_json()
        db = get_db()
        
        # Log the incoming data for debugging
        app.logger.info(f"Bulk upload data received: courses={data.get('courses', {})}, students={data.get('students', {})}")
        
        db.execute('BEGIN TRANSACTION')
        courses_added = students_added = enrollments_added = 0
        batches_created = 0
        
        # Handle courses - either existing IDs or new course data
        course_ids = []
        courses_data = data.get('courses', {})
        
        if 'existing' in courses_data:
            # Use existing course IDs
            course_ids = courses_data['existing']
        elif 'new' in courses_data:
            # Add new courses
            for course in courses_data['new']:
                course_level = 2 if course.get('parent_course_id') else 1
                db.execute('''INSERT INTO courses (course_code, course_name, instructor, schedule, 
                             parent_course_id, course_level, min_attendance_percentage)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (course['course_code'], course['course_name'], course['instructor'], 
                           course.get('schedule', ''), course.get('parent_course_id'), 
                           course_level, course.get('min_attendance_percentage', 75.0)))
                courses_added += 1
            
            # Get new course IDs
            for course in courses_data['new']:
                result = db.execute('SELECT id FROM courses WHERE course_code = ?', (course['course_code'],)).fetchone()
                if result:
                    course_ids.append(result['id'])
        
        # Handle students - either existing IDs or new student data
        student_ids = []
        students_data = data.get('students', {})
        
        if 'existing' in students_data:
            # Use existing student IDs
            student_ids = students_data['existing']
        elif 'new' in students_data:
            # First, create any new batches that don't exist
            batch_ids_map = {}
            for student in students_data['new']:
                batch_name = student.get('batch_name')
                if batch_name and batch_name not in batch_ids_map:
                    # Check if batch exists
                    existing_batch = db.execute('SELECT id FROM batches WHERE batch_name = ?', (batch_name,)).fetchone()
                    if existing_batch:
                        batch_ids_map[batch_name] = existing_batch['id']
                    else:
                        # Create new batch
                        from datetime import datetime
                        current_year = datetime.now().year
                        cursor = db.execute('''INSERT INTO batches (batch_name, batch_year, description)
                                             VALUES (?, ?, ?)''',
                                          (batch_name, current_year, f'Auto-created batch for {batch_name}'))
                        # Get the ID of the newly created batch
                        batch_ids_map[batch_name] = cursor.lastrowid
                        batches_created += 1
                        app.logger.info(f"Created new batch: {batch_name} with ID: {cursor.lastrowid}")
            
            # Now create students with proper batch_id
            for student in students_data['new']:
                batch_id = None
                batch_name = student.get('batch_name')
                if batch_name and batch_name in batch_ids_map:
                    batch_id = batch_ids_map[batch_name]
                
                app.logger.info(f"Creating student {student['student_id']} with batch_name='{batch_name}' and batch_id={batch_id}")
                
                db.execute('''INSERT INTO students (student_id, name, email, batch_id)
                             VALUES (?, ?, ?, ?)''',
                          (student['student_id'], student['name'], student['email'], batch_id))
                students_added += 1
            
            # Get new student IDs
            for student in students_data['new']:
                result = db.execute('SELECT id FROM students WHERE student_id = ?', (student['student_id'],)).fetchone()
                if result:
                    student_ids.append(result['id'])
        
        # Create enrollments
        for student_id in student_ids:
            for course_id in course_ids:
                course = db.execute('SELECT parent_course_id FROM courses WHERE id = ?', (course_id,)).fetchone()
                if course and course['parent_course_id']:  # Only sub-courses
                    existing = db.execute('SELECT id FROM enrollments WHERE student_id = ? AND course_id = ?',
                                        (student_id, course_id)).fetchone()
                    if not existing:
                        db.execute('''INSERT INTO enrollments (student_id, course_id, enrollment_type, is_active)
                                     VALUES (?, ?, 'direct', 1)''', (student_id, course_id))
                        enrollments_added += 1
        
        db.execute('COMMIT')
        
        # Log successful bulk upload
        log_user_action("BULK_UPLOAD", f"Finalized bulk upload: {courses_added} courses, {students_added} students, {enrollments_added} enrollments, {batches_created} batches", "BULK_UPLOAD", "")
        
        return jsonify({
            'success': True,
            'enrollment_count': enrollments_added,
            'summary': f"Added {courses_added} courses, {students_added} students, {enrollments_added} enrollments, {batches_created} batches"
        })
        
    except Exception as e:
        db.execute('ROLLBACK')
        log_user_action("BULK_UPLOAD", f"Failed to finalize bulk upload: {str(e)}", "BULK_UPLOAD", "", "FAILED")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/courses')
@admin_required
def api_courses():
    """Get all courses for selection"""
    db = get_db()
    courses = db.execute('''
        SELECT id, course_code, course_name, instructor, 
               COALESCE(schedule, '') as schedule 
        FROM courses 
        WHERE is_active = 1 AND parent_course_id IS NOT NULL
        ORDER BY course_name
    ''').fetchall()
    return jsonify([dict(course) for course in courses])

@app.route('/api/students')  
@admin_required
def api_students():
    """Get all students for selection with batch information"""
    db = get_db()
    students = db.execute('''
        SELECT s.id, s.student_id, s.name, s.email, 
               b.batch_name
        FROM students s 
        LEFT JOIN batches b ON s.batch_id = b.id 
        ORDER BY b.batch_name, s.name
    ''').fetchall()
    return jsonify([dict(student) for student in students])

@app.route('/reports')
@attendance_taker_required
def reports():
    """Reports page with various reporting options"""
    hierarchy = get_course_hierarchy()
    batches = get_student_batches()
    return render_template('reports.html', hierarchy=hierarchy, batches=batches)

@app.route('/clear_cache', methods=['GET', 'POST'])
@admin_required
def clear_cache():
    """Clear system cache"""
    try:
        cache_items_cleared = []
        
        # Clear face recognition cache
        if face_recognizer:
            face_recognizer.load_known_faces()
            cache_items_cleared.append('Face recognition data reloaded')
            app.logger.info('Face recognition cache cleared')
        
        # Log the cache clear action
        app.logger.info(f'Cache cleared by user {session.get("username", "unknown")}')
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully!',
            'items_cleared': cache_items_cleared,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        app.logger.error(f'Error clearing cache: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error clearing cache: {str(e)}'
        })

@app.route('/unenroll_student/<int:enrollment_id>')
@admin_required
def unenroll_student(enrollment_id):
    """Unenroll a student from a course"""
    db = get_db()
    
    # Get enrollment details
    enrollment = db.execute('''
        SELECT e.*, s.name as student_name, s.student_id, c.course_name FROM enrollments e 
         JOIN students s ON e.student_id = s.id 
         JOIN courses c ON e.course_id = c.id 
         WHERE e.id = ?''', (enrollment_id,)
    ).fetchone()
    
    if not enrollment:
        flash('Enrollment not found!', 'error')
        return redirect(url_for('enroll'))
    
    # Delete enrollment
    db.execute('DELETE FROM enrollments WHERE id = ?', (enrollment_id,))
    db.commit()
    
    # Log unenrollment
    log_user_action("UNENROLL", f"Unenrolled {enrollment['student_name']} ({enrollment['student_id']}) from {enrollment['course_name']}", "ENROLLMENT", enrollment_id)
    
    flash('Student unenrolled successfully!', 'success')
    return redirect(url_for('enroll'))

@app.route('/run_system_check', methods=['GET', 'POST'])
@admin_required
def run_system_check():
    """Run system diagnostic check"""
    try:
        app.logger.info(f'System check initiated by user: {session.get("username")}')
        db = get_db()
        
        # Basic system checks
        checks = {
            'database_connection': True,
            'student_count': db.execute('SELECT COUNT(*) FROM students').fetchone()[0],
            'course_count': db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],
            'user_count': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'enrollment_count': db.execute('SELECT COUNT(*) FROM enrollments').fetchone()[0],
            'attendance_records': db.execute('SELECT COUNT(*) FROM attendance').fetchone()[0],
            'batch_count': db.execute('SELECT COUNT(*) FROM batches').fetchone()[0],
            'disk_space': 'OK',
            'memory_usage': 'OK'
        }
        
        app.logger.info(f'System check completed: {checks["student_count"]} students, {checks["course_count"]} courses, {checks["attendance_records"]} attendance records')
        
        return jsonify({
            'success': True,
            'checks': checks,
            'message': 'System check completed successfully'
        })
        
    except Exception as e:
        app.logger.error(f'System check failed: {str(e)}')
        return jsonify({
            'success': False,
        'error': str(e),
            'message': 'System check failed'
        })

# Face Recognition API Endpoints
@app.route('/api/process_frame', methods=['POST'])
@attendance_taker_required
def process_frame():
    """Process a frame from webcam and recognize faces"""
    try:
        data = request.get_json()
        
        if not data or 'frame' not in data:
            return jsonify({'success': False, 'error': 'No frame data provided'})
        
        # Decode base64 frame
        frame_data = data['frame'].split(',')[1]  # Remove data:image/jpeg;base64,
        frame_bytes = base64.b64decode(frame_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'error': 'Invalid frame data'})
        
        # Initialize face recognizer if not already done
        global face_recognizer
        if face_recognizer is None:
            init_face_recognizer()
        
        # Recognize faces
        recognized_students, face_locations = face_recognizer.recognize_faces(frame)
        
        # Format response
        result = {
            'success': True,
            'faces_detected': len(face_locations),
            'recognized_students': recognized_students,
            'face_locations': face_locations
        }
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error processing frame: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mark_face_attendance', methods=['POST'])
@attendance_taker_required
def mark_face_attendance():
    """Mark attendance for recognized faces"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        student_ids = data.get('student_ids', [])
        
        if not course_id or not student_ids:
            return jsonify({'success': False, 'error': 'Missing course_id or student_ids'})
        
        db = get_db()
        from datetime import datetime
        now = datetime.now()
        today = now.date().isoformat()
        now_time = now.time().strftime('%H:%M:%S')
        
        # Get course info
        course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'success': False, 'error': 'Course not found'})
        
        marked_students = []
        already_marked = []
        
        for student_id in student_ids:
            # Get student info
            student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
            if not student:
                continue
            
            # Check if already marked today
            existing = db.execute(
                'SELECT id FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?',
                (student_id, course_id, today)
            ).fetchone()
            
            if not existing:
                # Mark attendance using the aggregation function
                mark_attendance_with_aggregation(
                    student_id=int(student_id),
                    course_id=int(course_id),
                    date=now.date(),
                    time=now_time,
                    status='Present'
                )
                marked_students.append({
                    'id': student['id'],
                    'name': student['name'],
                    'student_id': student['student_id']
                })
            else:
                already_marked.append({
                    'id': student['id'],
                    'name': student['name'],
                    'student_id': student['student_id']
                })
        
        # Log face recognition attendance
        log_user_action("FACE_RECOGNITION", f"Face recognition attendance marked for {len(marked_students)} students in course {course_id}", "ATTENDANCE", course_id)
        
        return jsonify({
            'success': True,
            'marked_students': marked_students,
            'already_marked': already_marked,
            'message': f'Attendance marked for {len(marked_students)} students via face recognition'
        })
        
    except Exception as e:
        app.logger.error(f"Error marking face attendance: {str(e)}")
        log_user_action("FACE_RECOGNITION", f"Failed to mark face recognition attendance for course {course_id}: {str(e)}", "ATTENDANCE", course_id, "FAILED")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reload_face_recognizer', methods=['POST'])
@admin_required
def reload_face_recognizer():
    """Reload face recognizer (useful after adding new student photos)"""
    try:
        global face_recognizer
        face_recognizer = FaceRecognizer()
        
        # Log face recognizer reload
        log_user_action("RELOAD", "Face recognizer reloaded", "SYSTEM", "face_recognizer")
        
        return jsonify({
            'success': True,
            'message': 'Face recognizer reloaded successfully',
            'loaded_faces': len(face_recognizer.known_face_encodings)
        })
        
    except Exception as e:
        app.logger.error(f"Error reloading face recognizer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# Initialize the application
if __name__ == '__main__':
    with app.app_context():
        init_db()
        # Initialize face recognizer
        try:
            init_face_recognizer()
            app.logger.info("Face recognizer initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize face recognizer: {str(e)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)