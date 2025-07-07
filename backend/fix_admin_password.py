#!/usr/bin/env python3
"""
Script pour corriger le mot de passe administrateur
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from models import db, User
from app import app

def fix_admin_password():
    """Corrige le mot de passe de l'administrateur"""
    with app.app_context():
        try:
            # Trouver l'utilisateur admin avec mot de passe non haché
            admin_user = User.query.filter_by(username='admin').first()

            if admin_user:
                # Vérifier si le mot de passe est déjà haché
                if admin_user.password_hash == 'admin123':
                    print("🔧 Correction du mot de passe administrateur...")

                    # Hacher le mot de passe
                    hashed_password = generate_password_hash('admin123')
                    admin_user.password_hash = hashed_password

                    db.session.commit()
                    print("✅ Mot de passe administrateur corrigé avec succès!")
                    print(f"   Utilisateur: {admin_user.username}")
                    print(f"   Mot de passe: admin123 (maintenant haché)")

                else:
                    print("ℹ️  Le mot de passe administrateur est déjà haché.")

            else:
                print("⚠️  Aucun utilisateur 'admin' trouvé.")

                # Créer un nouvel utilisateur admin
                print("🔧 Création d'un nouvel utilisateur administrateur...")
                new_admin = User(
                    username='admin',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(new_admin)
                db.session.commit()
                print("✅ Utilisateur administrateur créé avec succès!")
                print("   Utilisateur: admin")
                print("   Mot de passe: admin123")

        except Exception as e:
            print(f"❌ Erreur lors de la correction: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_admin_password()
