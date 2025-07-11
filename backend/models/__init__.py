
# Instance unique de SQLAlchemy pour toute l'application

from ..app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)

from datetime import datetime, timezone

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(255), default='Unknown')
    category = db.Column(db.String(255), default='General')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<FAQ {self.id}: {self.question[:50]}...>"

class PDFDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, server_default=db.func.now())
    description = db.Column(db.Text)

class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45))
    url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

class AdminActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255))
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
