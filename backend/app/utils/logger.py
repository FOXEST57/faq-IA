import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Create main logger
logger = logging.getLogger("faq_backend")
logger.setLevel(logging.DEBUG)

def setup_logger(app=None):
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'faq_backend.log')
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    
    # File handler (rotating logs)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024 * 100, backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # If app is provided, replace its logger
    if app:
        app.logger.handlers = []
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
    
    logger.info('Logger setup complete')