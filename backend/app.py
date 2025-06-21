from flask import Flask
from flask_cors import CORS # Import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Add this import
from view.hello import hello_bp
from view.faq import faq_bp
from view.pdf import pdf_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'faq.db')}"
db.init_app(app)

migrate = Migrate(app, db) # Add this line to initialize Flask-Migrate

app.register_blueprint(hello_bp)
app.register_blueprint(faq_bp)
app.register_blueprint(pdf_bp)


if __name__ == '__main__':
    app.run(debug=True)
