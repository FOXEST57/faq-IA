#!/bin/bash
# Script de démarrage pour l'API Flask avec le bon PYTHONPATH
cd "$(dirname "$0")"
source venv/bin/activate
export PYTHONPATH=.
# Cherche un processus sur le port 5000 et le tue si besoin
fuser -k 5000/tcp 2>/dev/null
python app.py
