import enum
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Enum


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    role = db.Column(db.String(20), nullable=False, default="user")  # 'admin' or 'user'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LocationList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String, nullable=False)
    entity = db.Column(db.String, nullable=True)        
    street_no = db.Column(db.String, nullable=True)     
    zip_place = db.Column(db.String, nullable=True)     
    phone = db.Column(db.String, nullable=True)         
    email = db.Column(db.String, nullable=True)         
    url = db.Column(db.String, nullable=True)           


class DurationEnum(enum.Enum):
    vormittag = "Vormittag"
    nachmittag = "Nachmittag"
    ganzer_tag = "ganzer Tag"

    def __str__(self):
        return self.value

class TipH(db.Model):
    __tablename__ = "tip_h"

    tiph_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    location = db.Column(db.String(64), nullable=False, index=True)
    username = db.Column(db.String(64), nullable=False, index=True)

    # 1:n relationship to TipD
    details = db.relationship("TipD", backref="header", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TipH id={self.tiph_id} location={self.location} user={self.username}>"


class TipD(db.Model):
    __tablename__ = "tip_d"

    tipd_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    tiph_id = db.Column(db.Integer, db.ForeignKey("tip_h.tiph_id"), nullable=False, index=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    duration = db.Column(Enum(DurationEnum, name="duration_enum"), nullable=False)
    amount_chf = db.Column(db.Numeric(10, 2), nullable=False, index=True)

    def __repr__(self):
        return f"<TipD id={self.tipd_id} user={self.username} CHF={self.amount_chf} header_id={self.tiph_id}>"
