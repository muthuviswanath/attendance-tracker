"""
WSGI entry point for production deployment
"""
import os
from app import app

# Set the environment
os.environ.setdefault('FLASK_ENV', 'production')

# Create the WSGI application
application = app

if __name__ == "__main__":
    application.run()
