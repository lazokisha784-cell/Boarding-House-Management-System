import os

# Base directory of the project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY', 'boarding-house-secret-key-2026')
    
    # Database URI: defaults to SQLite, or reads DATABASE_URL (handling Render's postgres:// prefix)
    _db_url = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'boarding_house.db')}")
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    
    # Disable modification tracking to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
