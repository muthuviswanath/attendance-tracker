# Attendance Tracker System

A comprehensive attendance tracking system built with Flask, OpenCV, and modern web technologies. Features multiple attendance marking methods including facial recognition, manual entry, quick check-in, and bulk upload capabilities.

## Features

### 🎯 Core Functionality
- **Multiple Attendance Methods**: 
  - **Facial Recognition**: LBPH-based face recognition with webcam integration
  - **Quick Check-in**: Student ID-based attendance marking
  - **Manual Entry**: Direct attendance marking by instructors
  - **Bulk Upload**: CSV-based bulk attendance processing
- **Student Management**: Complete student lifecycle management with photo support
- **Course Management**: Create and organize courses with instructor assignments
- **Batch Management**: Organize students into batches with bulk enrollment
- **User Management**: Role-based access control (Admin/Attendance Taker)
- **Comprehensive Reports**: Detailed attendance analytics and reporting

### 🚀 Technical Features
- **Web-based Interface**: Modern, responsive UI built with Bootstrap 5
- **Database Integration**: SQLite database with comprehensive schema
- **Real-time Processing**: Live webcam feed with LBPH face recognition
- **Secure Authentication**: Session-based user authentication system
- **File Upload**: Secure handling of student photos with validation
- **System Settings**: Configurable system parameters and preferences
- **Logging System**: Comprehensive activity logging and monitoring

## Installation

### Prerequisites
- Python 3.7 or higher
- Webcam/Camera device (for facial recognition)
- Windows/macOS/Linux operating system

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd AttendanceTracker
   ```

2. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your settings
   # Update SECRET_KEY and other configurations as needed
   ```

4. **Initialize the database**
   ```bash
   python app.py
   ```
   The application will automatically create the database and tables on first run.

5. **Create admin user**
   After starting the application, navigate to `/add_user` to create your first admin user.

6. **Access the application**
   Open your web browser and go to: `http://localhost:5000`

## Usage Guide

### 1. Initial Setup
1. **Create Admin User**: Go to `/add_user` and create an admin account
2. **Login**: Use your admin credentials to access the system
3. **Configure Settings**: Go to Settings to configure system parameters

### 2. Student Management
1. **Add Students**: Go to Students → Add New Student
   - Enter student ID, name, email, and batch
   - Upload a clear photo for facial recognition
   - System validates photo quality automatically

2. **Manage Batches**: Go to Batches → Add New Batch
   - Create student batches with attendance requirements
   - Set minimum attendance percentage per batch

### 3. Course Management
1. **Add Courses**: Go to Courses → Add New Course
   - Enter course code, name, instructor, and schedule
   - Courses can be enrolled by individual students or entire batches

### 4. Enrollment Management
1. **Individual Enrollment**: Go to Enrollment → Individual
   - Select students and courses to create enrollments
2. **Batch Enrollment**: Go to Batches → Manage Enrollments
   - Enroll entire batches in courses efficiently

### 5. Attendance Marking (Multiple Methods)

#### Method 1: Facial Recognition
1. Go to "Mark Attendance" → "Webcam Attendance"
2. Select the course
3. Students look at the camera one by one
4. System automatically recognizes and marks attendance

#### Method 2: Quick Check-in
1. Go to "Mark Attendance" → "Quick Check-in"
2. Select the course
3. Students enter their Student ID
4. System marks attendance instantly

#### Method 3: Manual Entry
1. Go to "Mark Attendance" → "Manual Entry"
2. Select the course
3. Mark attendance for each student manually

#### Method 4: Bulk Upload
1. Go to "Mark Attendance" → "Bulk Upload"
2. Upload CSV file with attendance data
3. System processes all entries automatically

### 6. Reports and Analytics
1. Go to "Reports" → "Attendance Report"
2. Filter by course, date range, student, or batch
3. View detailed attendance statistics
4. Export data for further analysis

## Project Structure

```
AttendanceTracker/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── wsgi.py                    # WSGI configuration for deployment
├── .env                       # Environment variables
├── .env.example              # Example environment file
├── attendance.db             # SQLite database
├── face_recognition_model.pkl # Face recognition model
├── templates/                # HTML templates
│   ├── base.html            # Base template with navigation
│   ├── index.html           # Dashboard
│   ├── login.html           # Login page
│   ├── students.html        # Student management
│   ├── add_student.html     # Add student form
│   ├── edit_student.html    # Edit student form
│   ├── courses.html         # Course management
│   ├── add_course.html      # Add course form
│   ├── edit_course.html     # Edit course form
│   ├── batches.html         # Batch management
│   ├── add_batch.html       # Add batch form
│   ├── edit_batch.html      # Edit batch form
│   ├── batch_enrollments.html # Batch enrollment management
│   ├── enroll.html          # Individual enrollment
│   ├── enrollment_manager.html # Enrollment management
│   ├── mark_attendance.html # Attendance method selection
│   ├── webcam_attendance.html # Webcam interface
│   ├── manual_attendance.html # Manual attendance entry
│   ├── quick_checkin.html   # Quick check-in interface
│   ├── bulk_attendance.html # Bulk attendance upload
│   ├── bulk_upload.html     # Bulk student upload
│   ├── reports.html         # Reports dashboard
│   ├── attendance_report.html # Detailed attendance report
│   ├── users.html           # User management
│   ├── add_user.html        # Add user form
│   ├── edit_user.html       # Edit user form
│   ├── settings.html        # System settings
│   └── system_logs.html     # System logs viewer
├── static/                  # Static files
│   ├── logos/              # Application logos
│   └── student_photos/     # Uploaded student photos
├── logs/                   # Application logs
│   └── attendance_system.log
└── backups/               # Database backups
```

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite with direct SQL queries
- **Computer Vision**: OpenCV for webcam handling and image processing
- **Face Recognition**: LBPH (Local Binary Patterns Histograms) algorithm
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Authentication**: Session-based user authentication
- **File Handling**: Werkzeug for secure uploads
- **Logging**: Python logging with rotating file handlers

## Database Schema

### Students Table
- ID (Primary Key), Student ID (Unique), Name, Email
- Photo path and face encoding (binary blob)
- Creation timestamp

### Courses Table
- ID (Primary Key), Course Code (Unique), Course Name
- Instructor, Schedule
- Creation timestamp

### Batches Table
- ID (Primary Key), Batch Name (Unique), Batch Year
- Description, Minimum Attendance Percentage
- Creation timestamp

### Enrollments Table
- ID (Primary Key), Student ID (Foreign Key), Course ID (Foreign Key)
- Enrollment timestamp

### Batch Course Enrollments Table
- ID (Primary Key), Batch ID (Foreign Key), Course ID (Foreign Key)
- Enrollment timestamp, Mandatory flag

### Attendance Table
- ID (Primary Key), Student ID (Foreign Key), Course ID (Foreign Key)
- Date, Time, Status (Present/Absent)
- Creation timestamp

### Users Table
- ID (Primary Key), Username (Unique), Password Hash
- Role (Admin/Attendance Taker), Full Name, Email
- Active status, Creation timestamp, Last login

### System Settings Table
- ID (Primary Key), Category, Setting Key, Setting Value
- Update timestamp

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User authentication
- `GET /logout` - User logout

### Dashboard
- `GET /` - Home page (redirects to login if not authenticated)
- `GET /dashboard` - Main dashboard

### Student Management
- `GET /students` - View all students
- `GET /add_student` - Add student form
- `POST /add_student` - Create new student
- `GET /edit_student/<id>` - Edit student form
- `POST /edit_student/<id>` - Update student
- `GET /delete_student/<id>` - Delete student

### Course Management
- `GET /courses` - View all courses
- `GET /add_course` - Add course form
- `POST /add_course` - Create new course
- `GET /edit_course/<id>` - Edit course form
- `POST /edit_course/<id>` - Update course
- `GET /delete_course/<id>` - Delete course

### Batch Management
- `GET /batches` - View all batches
- `GET /add_batch` - Add batch form
- `POST /add_batch` - Create new batch
- `GET /batch_enrollments/<id>` - Manage batch enrollments

### Enrollment Management
- `GET /enroll` - Individual enrollment interface
- `POST /bulk_enroll` - Bulk enrollment processing
- `GET /enrollment_manager` - Enrollment management dashboard

### Attendance Marking
- `GET /mark_attendance` - Attendance method selection
- `GET /webcam_attendance` - Webcam attendance interface
- `GET /manual_attendance/<course_id>` - Manual attendance form
- `GET /quick_checkin/<course_id>` - Quick check-in interface
- `POST /quick_checkin_submit` - Process quick check-in
- `GET /bulk_attendance/<course_id>` - Bulk attendance upload
- `POST /api/recognize_faces` - Face recognition API
- `POST /api/mark_webcam_attendance` - Mark webcam attendance

### Reports
- `GET /generate_report` - Generate attendance reports
- `GET /reports` - Reports dashboard

### User Management
- `GET /users` - View all users
- `GET /add_user` - Add user form
- `POST /add_user` - Create new user
- `GET /edit_user/<id>` - Edit user form
- `POST /edit_user/<id>` - Update user

### System Management
- `GET /settings` - System settings
- `GET /view_system_logs` - View system logs
- `GET /backup_database` - Database backup
- `POST /restore_database` - Database restoration

### Bulk Operations
- `GET /bulk_upload` - Bulk student upload interface
- `POST /bulk_upload_students` - Process bulk student upload

## Configuration

### Environment Variables (.env file)
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URI=sqlite:///attendance.db

# Upload Settings
UPLOAD_FOLDER=static/student_photos
MAX_CONTENT_LENGTH=16777216  # 16MB

# Face Recognition Settings
FACE_RECOGNITION_ENABLED=true
FACE_RECOGNITION_THRESHOLD=85

# Session Settings
SESSION_TIMEOUT=5  # minutes

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=logs/attendance_system.log
```

### System Settings (Configurable via UI)
- General system settings (application name, timezone, etc.)
- Attendance settings (marking methods, validation rules)
- Batch settings (default attendance requirements)
- User management settings
- Database backup and maintenance settings

## Troubleshooting

### Common Issues

1. **Face Recognition Not Working**
   - Ensure webcam is connected and working
   - Check camera permissions in browser
   - Verify student photos are clear and front-facing
   - Check face recognition is enabled in settings

2. **Login Issues**
   - Ensure you have created at least one admin user
   - Check username/password combination
   - Verify session timeout settings

3. **Database Issues**
   - Check database file permissions
   - Verify database file exists and is not corrupted
   - Try database backup/restore if needed

4. **Upload Issues**
   - Check file size limits (16MB default)
   - Verify supported file formats (JPG, PNG)
   - Ensure upload folder has write permissions

5. **Performance Issues**
   - Check system resources (CPU, memory)
   - Clean up old log files
   - Consider database optimization for large datasets

### Face Recognition Tips
- Use good quality webcam (720p or higher)
- Ensure adequate lighting conditions
- Process one student at a time for best results
- Update student photos if recognition accuracy decreases
- Clean lens regularly for clear image capture

### System Maintenance
- Regularly backup database
- Monitor log files for errors
- Clean up old attendance records periodically
- Update student photos when appearance changes significantly

## Development

### Adding New Features
1. Follow the existing Flask route patterns in `app.py`
2. Use direct SQL queries for database operations
3. Maintain Bootstrap 5 styling consistency
4. Add proper error handling and logging
5. Update this README with new functionality

### Database Management
- The application automatically creates tables on first run
- For schema changes, modify the `init_db()` function
- Use the migration system for data preservation
- Regular backups are recommended

### Code Structure
- **app.py**: Main application file with all routes and logic
- **config.py**: Configuration management
- **templates/**: Jinja2 HTML templates
- **static/**: Static assets (CSS, JS, images)
- **logs/**: Application logs
- **backups/**: Database backups

### Testing
- Test all attendance marking methods
- Verify face recognition accuracy with different lighting
- Test bulk upload functionality with sample data
- Validate user authentication and role permissions

## Security Considerations

- **User Authentication**: Session-based authentication with role-based access control
- **Password Security**: Passwords are hashed using secure algorithms
- **File Upload Security**: Uploaded files are validated and sanitized
- **Data Storage**: Student photos and face encodings stored locally
- **Session Management**: Configurable session timeout for security
- **Database Security**: SQLite database with proper file permissions
- **Input Validation**: All user inputs are validated and sanitized
- **Logging**: Comprehensive audit trail of all system activities

## Deployment

### Production Deployment
1. Set up a production WSGI server (e.g., Gunicorn)
2. Configure reverse proxy (e.g., Nginx)
3. Set up SSL/TLS certificates
4. Configure environment variables for production
5. Set up regular database backups
6. Monitor system logs and performance

### WSGI Configuration
The project includes `wsgi.py` for production deployment:
```python
from app import app
if __name__ == "__main__":
    app.run()
```

### Docker Deployment (Optional)
Consider containerizing the application for easier deployment and scaling.

## License

This project is for educational and internal use. Please ensure compliance with privacy regulations when handling student data and facial recognition information.

## Support

For issues and questions:
1. Check this README for common solutions
2. Review the troubleshooting section
3. Check system logs at Settings → View System Logs
4. Verify all system requirements are met
5. Check browser console for JavaScript errors

## Future Enhancements

- **Mobile Application**: Native mobile app for attendance marking
- **Advanced Analytics**: Machine learning-based attendance insights
- **Integration Features**: 
  - Email notifications for attendance alerts
  - SMS notifications for absent students
  - Calendar integration for automatic course scheduling
- **Export Options**: Multiple format exports (PDF, Excel, CSV)
- **Multi-camera Support**: Support for multiple webcam feeds
- **Cloud Storage**: Optional cloud backup and synchronization
- **API Integration**: REST API for third-party integrations
- **Advanced Reporting**: Custom report builder with charts and graphs

---

**Last Updated**: July 18, 2025  
**Version**: 2.0  
**Face Recognition**: LBPH-based system
