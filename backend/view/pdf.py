from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename

pdf_bp = Blueprint('pdf', __name__)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@pdf_bp.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    if file.content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large (max 10MB)'}), 400
    
    filename = secure_filename(file.filename)
    # In production, save to persistent storage
    file.save(os.path.join('uploads', filename))
    
    return jsonify({
        'message': 'File uploaded successfully',
        'filename': filename,
        'size': file.content_length
    })
