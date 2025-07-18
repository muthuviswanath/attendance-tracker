import sqlite3
import os

def check_database_and_files():
    """Check database content and file system"""
    
    # Check database
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    # Check table schema
    cursor.execute("PRAGMA table_info(students)")
    columns = cursor.fetchall()
    print("=== STUDENTS TABLE SCHEMA ===")
    for col in columns:
        print(f"  {col[1]} - {col[2]}")
    
    # Check student data
    cursor.execute("SELECT student_id, name, photo_path, face_encoding FROM students")
    students = cursor.fetchall()
    print("\n=== STUDENTS IN DATABASE ===")
    for student in students:
        print(f"  ID: {student[0]}")
        print(f"  Name: {student[1]}")
        print(f"  Photo Path: {student[2]}")
        print(f"  Face Encoding: {'Yes' if student[3] else 'No'}")
        print()
    
    conn.close()
    
    # Check files
    print("=== FILES IN STUDENT_PHOTOS ===")
    photos_dir = "static/student_photos"
    if os.path.exists(photos_dir):
        files = os.listdir(photos_dir)
        for file in files:
            print(f"  {file}")
        if not files:
            print("  (No files found)")
    else:
        print("  Directory doesn't exist")
    
    # Check photo path construction
    print("\n=== PHOTO PATH ANALYSIS ===")
    for student in students:
        if student[2]:  # has photo_path
            expected_path = f"static/student_photos/{student[2]}"
            full_path = os.path.join("static/student_photos", student[2])
            print(f"  {student[1]}:")
            print(f"    DB Path: {student[2]}")
            print(f"    Expected: {expected_path}")
            print(f"    Full Path: {full_path}")
            print(f"    Exists: {os.path.exists(full_path)}")
            print()

if __name__ == "__main__":
    check_database_and_files()
