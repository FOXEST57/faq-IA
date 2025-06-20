Here's a step-by-step guide to run the project locally with all required services:

### 1. Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL 14+
- Redis 6+
- Ollama (with Mistral model)
- Docker (optional for PostgreSQL/Redis)

### 2. Start Required Services

**Option 1: Using Docker (recommended):**
```bash
# Start PostgreSQL and Redis
docker run -d --name faq-db -p 5432:5432 -e POSTGRES_DB=faq_db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password postgres:14
docker run -d --name faq-redis -p 6379:6379 redis:6-alpine

# Start Ollama (if not installed locally)
docker run -d --name ollama -p 11434:11434 ollama/ollama
docker exec ollama ollama pull mistral
```

**Option 2: Manual installation:**
- Install and run PostgreSQL
- Install and run Redis
- Install Ollama and run:
  ```bash
  ollama serve &
  ollama pull mistral
  ```

### 3. Backend Setup
```bash
# Clone project (if not already)
git clone https://github.com/your-repo/ia-faq.git
cd ia-faq/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
echo "FLASK_ENV=development" > .env
echo "SECRET_KEY=your-secret-key" >> .env
echo "DATABASE_URL=postgresql://postgres:password@localhost:5432/faq_db" >> .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env
echo "EMBEDDING_MODEL=all-MiniLM-L6-v2" >> .env
echo "LLM_MODEL=mistral:latest" >> .env
echo "VECTOR_STORE_PATH=./data/vector_store.faiss" >> .env
echo "UPLOAD_FOLDER=./data/uploads" >> .env

# Initialize database
flask db init
flask db migrate
flask db upgrade

# Create upload directory
mkdir -p data/uploads
```

### 4. Frontend Setup
```bash
# In a new terminal
cd ia-faq/frontend

# Install dependencies
npm install

# Configure environment (create .env file)
echo "REACT_APP_API_URL=http://localhost:5000/api" > .env
```

### 5. Run the System

**Terminal 1: Backend Server**
```bash
cd ia-faq/backend
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
python run.py
```

**Terminal 2: Celery Worker**
```bash
cd ia-faq/backend
source venv/bin/activate
celery -A app.tasks.celery_tasks worker --loglevel=info
```

**Terminal 3: Frontend Server**
```bash
cd ia-faq/frontend
npm start
```

**Terminal 4: Ollama (if not using Docker)**
```bash
ollama serve
```

### 6. Verify Installation
- Backend: http://localhost:5000 (API docs)
- Frontend: http://localhost:3000
- Adminer (DB GUI): http://localhost:8080 (if using Docker)

### 7. Ingest Sample Documents
```bash
# After servers are running
curl -X POST -H "Authorization: Bearer <JWT_TOKEN>" \
  -F "file=@path/to/document.pdf" \
  http://localhost:5000/api/ingest/upload
```

### Key Endpoints
- **API Docs:** http://localhost:5000
- **FAQ Interface:** http://localhost:3000
- **Admin Login:** Use registered email/password

### Troubleshooting Tips:
1. **Database Issues:**
   ```bash
   flask db stamp head
   flask db migrate
   flask db upgrade
   ```

2. **Vector Store Initialization:**
   ```python
   from app.services.vector_store import vector_store
   vector_store.initialize_store()
   ```

3. **Reset System:**
   ```bash
   flask db drop
   flask db create
   flask db upgrade
   rm data/vector_store.faiss
   ```

4. **Monitor Services:**
   - Check logs in `backend/logs/faq_backend.log`
   - Use `docker logs <container-name>` for Docker services

This setup will run the complete system with:
- Flask backend on port 5000
- React frontend on port 3000
- PostgreSQL database
- Redis for caching
- Ollama with Mistral model
- Celery for background processing

All components will communicate locally with proper environment configuration.