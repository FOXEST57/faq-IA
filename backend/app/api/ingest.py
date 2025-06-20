import os
import uuid
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from app.core.security import admin_required
from app.tasks.celery_tasks import process_document_task
from app.utils.file_utils import allowed_file, secure_filename
from app.utils.logger import logger

ingest_bp = Blueprint('ingest', __name__)

@ingest_bp.route('/upload', methods=['POST'])
@jwt_required()
@admin_required
def upload_document():
    """
    Endpoint for uploading documents to be processed and added to the knowledge base.
    Accepts PDF files, saves them to the upload directory, and triggers background processing.
    """
    # Check if the file part exists in the request
    if 'file' not in request.files:
        logger.warning("Upload request without file part")
        return {"msg": "No file part in request"}, 400
        
    file = request.files['file']
    
    # Check if a file was selected
    if file.filename == '':
        logger.warning("Upload request with empty filename")
        return {"msg": "No selected file"}, 400
        
    # Validate file type
    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type attempted: {file.filename}")
        return {"msg": "File type not allowed. Only PDF files are accepted"}, 400
        
    # Secure filename and create unique path
    filename = secure_filename(file.filename)
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(upload_dir, unique_filename)
    
    try:
        # Save the file to the upload directory
        file.save(filepath)
        logger.info(f"File saved successfully: {filename} at {filepath}")
        
        # Trigger background processing task
        task = process_document_task.delay(filepath, filename)
        logger.info(f"Document processing task started for: {filename} (Task ID: {task.id})")
        
        return {
            "msg": "File uploaded successfully. Processing started.",
            "task_id": task.id,
            "filename": filename
        }, 202
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        # Clean up partially saved file if exists
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"msg": "File upload failed. Please try again."}, 500