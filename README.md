# Attendance Tracker System

A comprehensive facial recognition-based attendance tracking system built with Flask, OpenCV, and modern web technologies.

## Features

### 🎯 Core Functionality
- **Facial Recognition**: Automatically identify students using advanced face recognition
- **Real-time Attendance**: Mark attendance instantly through webcam integration
- **Student Management**: Add, view, and manage student profiles with photo registration
- **Course Management**: Create and organize courses with schedules
- **Enrollment System**: Enroll students in courses with relationship tracking
- **Comprehensive Reports**: Generate detailed attendance reports with filtering options

### 🚀 Technical Features
- **Web-based Interface**: Modern, responsive UI built with Bootstrap 5
- **Database Integration**: SQLite database with SQLAlchemy ORM
- **Real-time Processing**: Live webcam feed with instant face recognition
- **Secure File Upload**: Safe handling of student photos
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites
- Python 3.7 or higher
- Webcam/Camera device
- Windows/macOS/Linux operating system

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd AttendanceTracker
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your web browser and go to: `http://localhost:5000`

## Usage Guide

### 1. Initial Setup
1. **Add Students**: Go to Students → Add New Student
   - Enter student ID, name, and email
   - Upload a clear photo of the student's face
   - The system will automatically generate face encodings

2. **Create Courses**: Go to Courses → Add New Course
   - Enter course code, name, instructor, and schedule

3. **Enroll Students**: Go to Enrollment
   - Select students and courses to create enrollments

### 2. Marking Attendance
1. Go to "Mark Attendance"
2. Select the course
3. Click "Start Attendance Capture"
4. Students look at the camera one by one
5. System automatically recognizes and marks attendance

### 3. Viewing Reports
1. Go to "Reports" → "Attendance Report"
2. Filter by course, date range as needed
3. View detailed attendance records
4. Export data if required

## Project Structure

```
AttendanceTracker/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navigation
│   ├── index.html             # Home page
│   ├── students.html          # Student listing
│   ├── add_student.html       # Add student form
│   ├── courses.html           # Course listing
│   ├── add_course.html        # Add course form
│   ├── enroll.html            # Enrollment management
│   ├── mark_attendance.html   # Course selection for attendance
│   ├── webcam_attendance.html # Webcam interface
│   ├── reports.html           # Reports dashboard
│   └── attendance_report.html # Detailed attendance report
├── static/                    # Static files
│   └── student_photos/        # Uploaded student photos
└── .github/
    └── copilot-instructions.md # Development guidelines
```

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Computer Vision**: OpenCV for webcam handling
- **Face Recognition**: face_recognition library
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **File Handling**: Werkzeug for secure uploads

## Database Schema

### Students Table
- ID, Student ID, Name, Email
- Photo path and face encoding (binary)
- Creation timestamp

### Courses Table
- ID, Course Code, Course Name
- Instructor, Schedule
- Creation timestamp

### Enrollments Table
- Student ID, Course ID (foreign keys)
- Enrollment timestamp

### Attendance Table
- Student ID, Course ID (foreign keys)
- Date, Time, Status
- Creation timestamp

## API Endpoints

- `GET /` - Home page
- `GET /students` - View students
- `POST /add_student` - Add new student
- `GET /courses` - View courses
- `POST /add_course` - Add new course
- `GET /enroll` - Enrollment management
- `POST /enroll` - Create enrollment
- `POST /mark_attendance` - Select course for attendance
- `GET /webcam_attendance/<course_id>` - Webcam interface
- `POST /process_frame` - Process webcam frame for recognition
- `GET /reports` - Reports dashboard
- `GET /attendance_report` - Detailed attendance report

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `SQLALCHEMY_DATABASE_URI`: Database connection string

### File Upload Settings
- Supported formats: JPG, PNG
- Storage location: `static/student_photos/`
- Automatic face encoding generation

## Troubleshooting

### Common Issues

1. **Camera not working**
   - Check camera permissions in browser
   - Ensure camera is not used by other applications
   - Try different browsers (Chrome recommended)

2. **Face recognition not accurate**
   - Ensure good lighting conditions
   - Use clear, front-facing photos
   - Retake photos if recognition fails

3. **Installation issues**
   - Install Visual Studio Build Tools (Windows)
   - Install cmake and dlib dependencies
   - Use conda environment if pip fails

### Performance Tips
- Use good quality webcam (720p or higher)
- Ensure adequate lighting
- Process one student at a time for best results
- Regularly clean up old attendance records

## Development

### Adding New Features
1. Follow the existing Flask route patterns
2. Use SQLAlchemy for database operations
3. Maintain Bootstrap styling consistency
4. Add proper error handling
5. Update this README

### Database Migrations
The application automatically creates tables on first run. For schema changes:
1. Modify models in `app.py`
2. Delete `attendance.db` file
3. Restart application to recreate tables

## Security Considerations

- Student photos are stored locally
- Face encodings are stored securely in database
- File uploads are validated and sanitized
- Session management for web interface
- No external API dependencies for face recognition

## License

This project is for educational and internal use. Please ensure compliance with privacy regulations when handling student data.

## Support

For issues and questions:
1. Check this README for common solutions
2. Review the troubleshooting section
3. Check browser console for JavaScript errors
4. Verify camera permissions and hardware

## Future Enhancements

- Multiple camera support
- Advanced analytics and insights
- Email notifications for attendance
- Mobile app integration
- Cloud storage options
- Advanced reporting features
