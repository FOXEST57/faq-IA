# Ajout d'un blueprint Flask pour l'upload et la gestion des PDF (upload et listing).

from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
from models import db, PDFDocument
# import fitz  # PyMuPDF pour l'extraction de texte

# Création d'un blueprint Flask pour la gestion des PDF
pdf_bp = Blueprint('pdf', __name__)
# Définition du dossier où seront stockés les fichiers uploadés
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
# Définition des extensions autorisées (ici uniquement PDF)
ALLOWED_EXTENSIONS = {'pdf'}

# Fonction utilitaire pour vérifier l'extension du fichier
def allowed_file(filename):
    # Vérifie que le nom contient un point et que l'extension est dans la liste autorisée
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route pour uploader un fichier PDF
@pdf_bp.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    # Vérifie qu'un fichier a bien été envoyé dans la requête
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé.'}), 400
    file = request.files['file']
    # Vérifie que le nom du fichier n'est pas vide
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide.'}), 400
    # Vérifie que le fichier existe et que son extension est autorisée
    if file and allowed_file(file.filename):
        # Sécurise le nom du fichier pour éviter les problèmes de chemin
        filename = secure_filename(file.filename)
        # Sauvegarde le fichier dans le dossier UPLOAD_FOLDER
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        # Récupère une éventuelle description envoyée dans le formulaire
        description = request.form.get('description', '')
        # Crée une nouvelle entrée PDFDocument en base de données
        pdf_doc = PDFDocument(filename=filename, description=description)
        # Ajoute l'entrée en base de données et valide la transaction
        db.session.add(pdf_doc)
        db.session.commit()
        # Retourne une réponse JSON avec un message de succès et l'id du document
        return jsonify({'message': 'Fichier uploadé.', 'id': pdf_doc.id, 'filename': filename}), 201
    else:
        # Si le fichier n'est pas autorisé, retourne une erreur
        return jsonify({'error': 'Format de fichier non autorisé.'}), 400

# Route pour lister les PDF uploadés
@pdf_bp.route('/api/pdf', methods=['GET'])
def list_pdfs():
    # Récupère tous les documents PDF enregistrés en base
    pdfs = PDFDocument.query.all()
    # Retourne la liste des PDF sous forme de JSON
    return jsonify([
        {
            'id': pdf.id,
            'filename': pdf.filename,
            'upload_date': str(pdf.upload_date) if pdf.upload_date else None,
            'description': pdf.description
        } for pdf in pdfs
    ])

# Route pour extraire le texte d'un PDF par son id
@pdf_bp.route('/api/pdf/extract/<int:pdf_id>', methods=['GET'])
def extract_pdf_text(pdf_id):
    # Recherche le document PDF en base
    pdf_doc = PDFDocument.query.get_or_404(pdf_id)
    # Construit le chemin complet du fichier PDF
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_doc.filename)
    # Vérifie que le fichier existe bien sur le disque
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'Fichier PDF introuvable sur le serveur.'}), 404
    # Ouvre le PDF et extrait le texte de chaque page
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    # Retourne le texte extrait sous forme de JSON
    return jsonify({'id': pdf_id, 'filename': pdf_doc.filename, 'text': text})
