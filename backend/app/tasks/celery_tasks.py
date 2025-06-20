from celery import shared_task
from app.utils.logger import logger
from app.services.vector_store import VectorStore
from app.core.config import Config

@shared_task(bind=True, max_retries=3)
def process_document_task(self, file_path, file_name):
    try:
        # Create vector store instance with config
        config = {
            'EMBEDDING_MODEL': os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
            'VECTOR_STORE_PATH': os.getenv('VECTOR_STORE_PATH', '/data/vector_store.faiss')
        }
        vector_store = VectorStore(config)
        
        from app.services.document_service import ingest_document
        success = ingest_document(file_path, file_name, vector_store)
        if success:
            return {"status": "success", "file": file_name}
        else:
            return {"status": "skipped", "reason": "duplicate"}
    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}")
        self.retry(exc=e, countdown=60)