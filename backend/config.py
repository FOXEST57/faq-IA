import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600
    }
    REDIS_URL = os.getenv('REDIS_URL')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
    LLM_MODEL = os.getenv('LLM_MODEL')
    VECTOR_STORE_PATH = os.getenv('VECTOR_STORE_PATH')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 10485760))
    JWT_SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour