#!/usr/bin/env python3
"""
Script d'initialisation de la base de données PostgreSQL
Lance ce script après avoir déployé l'application pour créer les tables
"""

import os
import sys
from pathlib import Path

# Ajouter le dossier backend au path Python
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app import create_app
from models import db

def init_database():
    """Initialise la base de données PostgreSQL"""
    print("🔄 Initialisation de la base de données PostgreSQL...")

    # Créer l'application avec la configuration de production
    app = create_app('production')

    with app.app_context():
        try:
            # Créer toutes les tables
            db.create_all()
            print("✅ Tables créées avec succès!")

            # Vérifier les tables créées
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tables créées: {', '.join(tables)}")

        except Exception as e:
            print(f"❌ Erreur lors de la création des tables: {e}")
            return False

    return True

if __name__ == "__main__":
    success = init_database()
    if success:
        print("\n🎉 Base de données initialisée avec succès!")
        print("Vous pouvez maintenant redémarrer Gunicorn.")
    else:
        print("\n💥 Échec de l'initialisation de la base de données.")
        sys.exit(1)
