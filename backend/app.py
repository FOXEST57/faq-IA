from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from view.faq import faq_bp
from view.pdf import pdf_bp
from models import db, User, FAQ, PDFDocument, VisitLog, AdminActionLog
from config import config
import os
import flask
from werkzeug.security import check_password_hash
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            flash("Accès réservé aux administrateurs.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

    @app.route('/admin/users')
    @admin_required
    def admin_users():
        users = User.query.all()
        return render_template('admin_users.html', users=users)

    @app.route('/admin/users/add', methods=['GET', 'POST'])
    @admin_required
    def add_user():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            is_admin = bool(request.form.get('is_admin'))
            if not username or not password:
                flash("Nom d'utilisateur et mot de passe requis.", "danger")
                return render_template('admin_user_form.html')
            if User.query.filter_by(username=username).first():
                flash("Nom d'utilisateur déjà utilisé.", "danger")
                return render_template('admin_user_form.html')
            from werkzeug.security import generate_password_hash
            user = User(username=username, password_hash=generate_password_hash(password), is_admin=is_admin)
            db.session.add(user)
            db.session.commit()
            flash("Administrateur ajouté avec succès.", "success")
            return redirect(url_for('admin_users'))
        return render_template('admin_user_form.html')

    @app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
    @admin_required
    def edit_user(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            username = request.form.get('username')
            is_admin = bool(request.form.get('is_admin'))
            if not username:
                flash("Nom d'utilisateur requis.", "danger")
                return render_template('admin_user_form.html', user=user, edit=True)
            if User.query.filter(User.username == username, User.id != user.id).first():
                flash("Nom d'utilisateur déjà utilisé.", "danger")
                return render_template('admin_user_form.html', user=user, edit=True)
            user.username = username
            user.is_admin = is_admin
            password = request.form.get('password')
            if password:
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Utilisateur modifié avec succès.", "success")
            return redirect(url_for('admin_users'))
        return render_template('admin_user_form.html', user=user, edit=True)

    @app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
    @admin_required
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == session.get('user_id'):
            flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
            return redirect(url_for('admin_users'))
        db.session.delete(user)
        db.session.commit()
        flash("Utilisateur supprimé avec succès.", "success")
        return redirect(url_for('admin_users'))

    app.register_blueprint(faq_bp)
    app.register_blueprint(pdf_bp)

    app.secret_key = app.config.get('SECRET_KEY', 'dev')

    return app

# Pour compatibilité avec Gunicorn
app = create_app()

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        return render_template('contact.html', success=True, name=name)
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and password == user.password_hash:  # Temporaire: comparaison directe car mot de passe en clair
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

if __name__ == '__main__':
    # Mode développement seulement
    app.run(debug=True, host='0.0.0.0', port=8000)
