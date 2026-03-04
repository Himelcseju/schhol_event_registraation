"""
Configuration. In production, set environment variables; defaults are for local dev.
"""
import os

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY") or "school-event-portal-dev-change-in-production"
# Debug on by default when running locally (python app.py). Set FLASK_ENV=production to turn off.
DEBUG = os.environ.get("FLASK_ENV", "development") != "production"

# Database (production: set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST") or "localhost",
    "user": os.environ.get("DB_USER") or "root",
    "password": os.environ.get("DB_PASSWORD") or "root",
    "database": os.environ.get("DB_NAME") or "school_event",
    "charset": "utf8mb4",
}

# Branding
SCHOOL_NAME = os.environ.get("SCHOOL_NAME") or "School Event Portal"

# Default batch name (created in DB if missing)
DEFAULT_BATCH_NAME = os.environ.get("DEFAULT_BATCH_NAME") or "2008"

# Site maintenance donation (auto, read-only on registration)
SITE_FEE = int(os.environ.get("SITE_FEE") or "20")

# Admin password (production: must set ADMIN_PASSWORD)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "admin123"
