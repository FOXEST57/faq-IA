from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from backend.app.services.ollama_service import OllamaService # Changed to absolute import
import os

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/faq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Ollama Service
ollama_service = OllamaService()

# Import models to register them with SQLAlchemy
from backend.models import FAQ # Changed to absolute import

@app.route('/')
def hello():
    return jsonify(message="Welcome to the FAQ Generator Backend!")

@app.route('/status/ollama')
def ollama_status():
    status = ollama_service.check_ollama_status()
    return jsonify(status="running" if status else "not_running")

@app.route('/faqs', methods=['GET'])
def get_faqs():
    faqs = FAQ.query.all()
    return jsonify([{'id': faq.id, 'question': faq.question, 'answer': faq.answer, 'source': faq.source, 'category': faq.category} for faq in faqs])

@app.route('/faqs', methods=['POST'])
def add_faq():
    data = request.get_json()
    if not data or not all(k in data for k in ('question', 'answer')):
        return jsonify(error="Missing question or answer"), 400
    
    new_faq = FAQ(
        question=data['question'],
        answer=data['answer'],
        source=data.get('source', 'API'),
        category=data.get('category', 'General')
    )
    db.session.add(new_faq)
    db.session.commit()
    return jsonify(message="FAQ added successfully", id=new_faq.id), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create tables if they don't exist
    app.run(debug=True, host='0.0.0.0', port=5000)
