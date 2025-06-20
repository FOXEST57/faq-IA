from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from view.hello import hello_bp
from view.faq import faq_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'faq.db')}"
db.init_app(app)

app.register_blueprint(hello_bp)
app.register_blueprint(faq_bp)

@app.route('/')
def hello():
    return "Hello, Flask!"

@app.route('/test_db')
def test_db():
    try:
        from models import FAQ
        count = FAQ.query.count()
        return f"Connexion OK. Nombre de FAQ : {count}"
    except Exception as e:
        return f"Erreur de connexion à la BDD : {e}"

if __name__ == '__main__':
    app.run(debug=True)
