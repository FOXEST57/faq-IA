# Ajout d'un blueprint Flask pour l'upload et la gestion des PDF (upload et listing).

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
from models import db, PDFDocument
import fitz  # PyMuPDF pour l'extraction de texte
from functools import wraps
from utils.ollama_rag import OllamaRAGService

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            flash("Accès réservé aux administrateurs.", "danger")
            return redirect('/login')  # URL directe au lieu de url_for
        return f(*args, **kwargs)
    return decorated_function

@pdf_bp.route('/admin/pdfs')
@admin_required
def admin_pdf_list():
    try:
        pdfs = PDFDocument.query.order_by(PDFDocument.upload_date.desc()).all()
        print(f"DEBUG: Nombre de PDFs trouvés: {len(pdfs)}")  # Pour debug
        return render_template('admin_pdf_list.html', pdfs=pdfs)
    except Exception as e:
        print(f"DEBUG: Erreur dans admin_pdf_list: {e}")
        flash(f"Erreur lors du chargement des PDF: {str(e)}", "danger")
        return render_template('admin_pdf_list.html', pdfs=[])

@pdf_bp.route('/admin/pdfs/upload', methods=['GET', 'POST'])
@admin_required
def admin_pdf_upload():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('Aucun fichier sélectionné.', 'danger')
            return render_template('admin_pdf_upload.html')

        file = request.files['pdf_file']
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'danger')
            return render_template('admin_pdf_upload.html')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Créer le dossier uploads s'il n'existe pas
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            description = request.form.get('description', '')
            pdf_doc = PDFDocument(filename=filename, description=description)
            db.session.add(pdf_doc)
            db.session.commit()

            flash('PDF uploadé avec succès.', 'success')
            return redirect(url_for('pdf.admin_pdf_list'))
        else:
            flash('Format de fichier non autorisé. Seuls les PDF sont acceptés.', 'danger')

    return render_template('admin_pdf_upload.html')

@pdf_bp.route('/admin/pdfs/delete/<int:pdf_id>', methods=['POST'])
@admin_required
def admin_delete_pdf(pdf_id):
    pdf_doc = PDFDocument.query.get_or_404(pdf_id)
    # Supprimer le fichier physique
    filepath = os.path.join(UPLOAD_FOLDER, pdf_doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    # Supprimer l'entrée en base
    db.session.delete(pdf_doc)
    db.session.commit()
    flash('PDF supprimé avec succès.', 'success')
    return redirect(url_for('pdf.admin_pdf_list'))

@pdf_bp.route('/admin/ia/generation')
@admin_required
def admin_ia_generation():
    """Interface de génération de FAQ par IA"""
    # Vérifier le statut d'Ollama
    rag_service = OllamaRAGService()
    ollama_status = rag_service.check_ollama_connection()
    current_model = rag_service.model if ollama_status else "Non disponible"

    # Récupérer les PDF disponibles
    pdfs = PDFDocument.query.order_by(PDFDocument.upload_date.desc()).all()

    # Récupérer les FAQ générées en attente (on pourrait ajouter un champ status plus tard)
    pending_faqs = []  # Pour l'instant, on peut utiliser les FAQ avec source='ia' récentes

    return render_template('admin_ia_generation.html',
                         ollama_status=ollama_status,
                         current_model=current_model,
                         pdfs=pdfs,
                         pending_faqs=pending_faqs)

@pdf_bp.route('/admin/ia/generate-faq', methods=['POST'])
@admin_required
def generate_faq_from_pdf():
    """Génère des FAQ à partir d'un PDF sélectionné"""
    pdf_id = request.form.get('pdf_id')
    if not pdf_id:
        flash('Veuillez sélectionner un PDF.', 'danger')
        return redirect(url_for('pdf.admin_ia_generation'))

    pdf_doc = PDFDocument.query.get_or_404(pdf_id)
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_doc.filename)

    if not os.path.exists(pdf_path):
        flash('Fichier PDF introuvable.', 'danger')
        return redirect(url_for('pdf.admin_ia_generation'))

    try:
        # Initialiser le service RAG
        rag_service = OllamaRAGService()

        # Vérifier la connexion Ollama
        if not rag_service.check_ollama_connection():
            flash('Ollama n\'est pas disponible. Vérifiez le service.', 'danger')
            return redirect(url_for('pdf.admin_ia_generation'))

        # Générer les FAQ
        generated_faqs = rag_service.process_pdf_to_faq(pdf_path)

        if not generated_faqs:
            flash('Aucune FAQ générée. Le document pourrait être trop court ou illisible.', 'warning')
            return redirect(url_for('pdf.admin_ia_generation'))

        # Sauvegarder les FAQ générées
        saved_count = 0
        for faq_data in generated_faqs:
            if faq_data.get('question') and faq_data.get('answer'):
                faq = FAQ(
                    question=faq_data['question'],
                    answer=faq_data['answer'],
                    source='ia'
                )
                db.session.add(faq)
                saved_count += 1

        db.session.commit()

        flash(f'{saved_count} FAQ générées avec succès à partir du document {pdf_doc.filename}.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la génération: {str(e)}', 'danger')

    return redirect(url_for('pdf.admin_ia_generation'))
