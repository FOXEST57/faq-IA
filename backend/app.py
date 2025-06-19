from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///faq.db'
db = SQLAlchemy(app)

# Modèle Utilisateur (administrateur)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)

# Modèle FAQ
class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), nullable=False)  # 'manuel' ou 'ia'
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

# Modèle Document PDF
class PDFDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, server_default=db.func.now())
    description = db.Column(db.Text)

# Modèle Log de visite
class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45))
    url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Modèle Log d'action admin
class AdminActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255))
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

@app.route('/')
def hello():
    return "Hello, Flask!"

@app.route('/api/hello')
def hello_api():
    return {"message": "Hello depuis Flask!"}

if __name__ == '__main__':
    app.run(debug=True)
