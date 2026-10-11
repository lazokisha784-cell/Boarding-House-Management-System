import os

# Base directory of the project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY', 'boarding-house-secret-key-2026')
    
    # SQLite database will be saved permanently as 'boarding_house.db' inside project folder
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'boarding_house.db')}"
    )
    
    # Disable modification tracking to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
