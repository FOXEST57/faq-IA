from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from view.hello import hello_bp
from view.faq import faq_bp
from view.pdf import pdf_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'faq.db')}"
db.init_app(app)

# Filtre Jinja2 personnalisé pour convertir les sauts de ligne en <br>
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convertit les sauts de ligne en balises <br>"""
    if text is None:
        return ''
    return text.replace('\n', '<br>\n')

app.register_blueprint(hello_bp)
app.register_blueprint(faq_bp)
app.register_blueprint(pdf_bp)


if __name__ == '__main__':
    app.run(debug=True)
