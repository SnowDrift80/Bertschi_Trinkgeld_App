# setup_db.py
from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("All database tables created (if they didn't exist).")
