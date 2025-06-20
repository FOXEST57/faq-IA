from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.core.config import Config
from app.db.base import Base
from app.utils.logger import setup_logger, logger

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    setup_logger(app)
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    
    # Initialize vector store
    from app.services.vector_store import VectorStore
    app.vector_store = VectorStore(app.config)
    logger.info("Vector store initialized")
    
    from app.api.auth import auth_bp
    from app.api.faq import faq_bp
    from app.api.ingest import ingest_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(faq_bp, url_prefix='/api/faq')
    app.register_blueprint(ingest_bp, url_prefix='/api/ingest')
    
    return app