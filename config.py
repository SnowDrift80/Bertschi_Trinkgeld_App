import os
import os.path

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _db_uri():
    uri = os.getenv("DATABASE_URL")
    if uri:
        return uri
    user = os.getenv("PGUSER", "trinkgelduser")
    pw   = os.getenv("PGPASSWORD", "txm9272")
    host = os.getenv("PGHOST", "db")
    port = os.getenv("PGPORT", "5432")
    db   = os.getenv("PGDATABASE", "trinkgeld")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"

class Config:
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", "14400"))
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
