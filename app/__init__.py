from flask import Flask
from flask_migrate import Migrate  # 🔹 Add this
from flask_wtf import CSRFProtect
from .models import db
from .routes import setup_routes
from config import Config

migrate = Migrate()  # 🔹 Create Migrate instance

csrf = CSRFProtect()  # 🔹 Initialize CSRF protection

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    csrf.init_app(app)  # 🔹 Initialize CSRF protection with the app

    db.init_app(app)
    migrate.init_app(app, db)  # 🔹 Hook Migrate into your app

    setup_routes(app)

    return app
