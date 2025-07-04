from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from view.faq import faq_bp
from view.pdf import pdf_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
from config import config
import os

def create_app(config_name=None):
    """Factory pour créer l'application Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

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

    return app

# Pour compatibilité avec Gunicorn
app = create_app()

if __name__ == '__main__':
    # Mode développement seulement
    app.run(debug=True, host='0.0.0.0', port=8000)
