<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Attendance Tracker System - Copilot Instructions

This is a Flask-based attendance tracking system with facial recognition capabilities.

## Project Structure
- `app.py` - Main Flask application with routes and database models
- `templates/` - HTML templates using Bootstrap for styling
- `static/` - Static files including student photos
- `requirements.txt` - Python dependencies

## Key Technologies
- **Flask** - Web framework
- **OpenCV** - Computer vision and webcam handling
- **face_recognition** - Facial recognition library
- **SQLAlchemy** - Database ORM
- **Bootstrap 5** - Frontend styling
- **SQLite** - Database

## Database Models
- **Student** - Student information and face encodings
- **Course** - Course details
- **Enrollment** - Student-course relationships
- **Attendance** - Attendance records

## Key Features
- Facial recognition-based attendance marking
- Student and course management
- Real-time webcam integration
- Attendance reporting and analytics
- Bootstrap-based responsive UI

## Development Guidelines
- Follow Flask best practices
- Use SQLAlchemy for database operations
- Maintain responsive design with Bootstrap
- Handle errors gracefully in face recognition
- Ensure proper file upload security
- Use proper HTTP status codes and error handling
