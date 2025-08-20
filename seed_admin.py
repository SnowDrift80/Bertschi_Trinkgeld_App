# seed/seed_admin.py

from app import create_app
from app.models import db, User

app = create_app()

with app.app_context():
    db.create_all()  # ensure tables are created

    admin_email = "admin@recycling-paradies.ch"
    existing_admin = User.query.filter_by(email=admin_email).first()

    if existing_admin:
        print("Admin user already exists.")
    else:
        admin = User(
            email=admin_email,
            name="Admin",
            location="HQ",
            role="superadmin"
        )
        admin.set_password("admin123")  # choose a safe password in real life!
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
