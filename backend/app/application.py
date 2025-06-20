from app import create_app
from app.core.config import Config

app = create_app(Config)

# Import tasks after app creation to ensure context
from app.tasks import celery_tasks

if __name__ == '__main__':
    app.run()