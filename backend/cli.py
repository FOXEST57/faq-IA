from app.application import app
from flask_migrate import Migrate
from app import db

migrate = Migrate(app, db)

@app.cli.command("init-db")
def init_db():
    """Initialize the database"""
    from flask_migrate import init, migrate, upgrade
    
    try:
        init()
        print("Database initialized")
    except Exception as e:
        print(f"Database initialization skipped: {str(e)}")
    
    migrate(message="Initial migration")
    upgrade()
    print("Database migration complete")

@app.cli.command("run-worker")
def run_worker():
    """Start Celery worker"""
    from app.tasks.celery_tasks import celery_app
    worker = celery_app.Worker(loglevel="info")
    worker.start()