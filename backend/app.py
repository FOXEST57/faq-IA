from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from view.hello import hello_bp
from view.faq import faq_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///faq.db'
db.init_app(app)

app.register_blueprint(hello_bp)
app.register_blueprint(faq_bp)

@app.route('/')
def hello():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)
