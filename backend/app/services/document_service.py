import os
import uuid
import hashlib
import pdfplumber
from app.utils.logger import logger
from app.utils.file_utils import secure_filename, allowed_file
from app.db.session import SessionLocal
from app.db.models import Document
from .vector_store import VectorStore # Changed from 'vector_store' to 'VectorStore'
from sentence_transformers import util

def process_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text
    except Exception as e:
        logger.error(f"PDF processing failed: {str(e)}")
        raise ValueError("Failed to process PDF file")

def extract_text(file_path):
    if file_path.lower().endswith('.pdf'):
        return process_pdf(file_path)
    else:
        raise ValueError("Unsupported file type")

def compute_file_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def ingest_document(file_path, file_name, vector_store):
    file_hash = compute_file_hash(file_path)
    
    db = SessionLocal()
    try:
        # Check if document already exists
        existing = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing:
            logger.info(f"Document already exists: {file_name}")
            return False
        
        # Process document
        content = extract_text(file_path)
        
        # Create new document record
        doc = Document(
            file_name=file_name,
            file_hash=file_hash,
            content=content,
            embedding_model=os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Get vector store instance
        vector_store_instance = VectorStore.get_instance() # Get the instance here
    
        # Add to vector store
        doc_id = str(doc.id)
        from flask import current_app
        vector_store_instance.add_documents( # Use the instance here
            [content], 
            [{'id': doc_id}]
        )
        
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Document ingestion failed: {str(e)}")
        raise
    finally:
        db.close()