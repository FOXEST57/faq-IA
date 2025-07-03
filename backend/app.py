from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
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

# Route principale qui affiche la page FAQ
@app.route('/')
def index():
    """Page d'accueil qui affiche l'interface FAQ"""
    faqs = FAQ.query.order_by(FAQ.created_at.desc()).all()
    return render_template('faq_list.html', faqs=faqs)

app.register_blueprint(faq_bp)
app.register_blueprint(pdf_bp)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
