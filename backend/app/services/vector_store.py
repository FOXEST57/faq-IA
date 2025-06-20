import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from app.utils.logger import logger
from app.db.session import SessionLocal
from app.db.models import Document

class VectorStore:
    def __init__(self, config):
        self.config = config
        self.embedder = None
        self.index = None
        self.doc_ids = []
        self.initialize_store()
    
    def initialize_store(self):
        try:
            self.embedder = SentenceTransformer(self.config['EMBEDDING_MODEL'])
            
            if os.path.exists(self.config['VECTOR_STORE_PATH']):
                self.index = faiss.read_index(self.config['VECTOR_STORE_PATH'])
                self.load_document_ids()
                logger.info("Loaded existing vector store")
            else:
                self.create_new_index()
                logger.info("Created new vector store index")
        except Exception as e:
            logger.error(f"Vector store initialization failed: {str(e)}")
            raise
    
    def create_new_index(self):
        dim = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexHNSWFlat(dim, 32)
        self.index.hnsw.efSearch = 128
        self.doc_ids = []
    
    def load_document_ids(self):
        db = SessionLocal()
        try:
            self.doc_ids = [str(doc.id) for doc in db.query(Document).all()]
        finally:
            db.close()
    
    def add_documents(self, texts, metadata_list):
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        self.index.add(embeddings)
        self.doc_ids.extend([meta['id'] for meta in metadata_list])
        self.save_index()
    
    def search(self, query, k=5):
        query_embedding = self.embedder.encode([query])
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx >= 0:
                doc_id = self.doc_ids[idx]
                results.append({
                    'id': doc_id,
                    'score': float(1 - distance),
                    'index': int(idx)
                })
        return results
    
    def save_index(self):
        faiss.write_index(self.index, self.config['VECTOR_STORE_PATH'])