from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from view.faq import faq_bp
from view.pdf import pdf_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
from config import config
import os
import flask
from werkzeug.security import check_password_hash

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

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if flask.request.method == 'POST':
            # Ici, tu pourrais traiter le formulaire (envoyer un mail, stocker, etc.)
            name = flask.request.form.get('name')
            email = flask.request.form.get('email')
            message = flask.request.form.get('message')
            # Pour l'instant, on affiche juste un message de confirmation
            return render_template('contact.html', success=True, name=name)
        return render_template('contact.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['is_admin'] = user.is_admin
                flash('Connexion réussie.', 'success')
                return redirect(url_for('faq.faq_list'))
            else:
                return render_template('login.html', error="Nom d'utilisateur ou mot de passe incorrect.")
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Déconnexion réussie.', 'info')
        return redirect(url_for('faq.faq_list'))

    app.register_blueprint(faq_bp)
    app.register_blueprint(pdf_bp)

    app.secret_key = app.config.get('SECRET_KEY', 'dev')

    return app

# Pour compatibilité avec Gunicorn
app = create_app()

if __name__ == '__main__':
    # Mode développement seulement
    app.run(debug=True, host='0.0.0.0', port=8000)
