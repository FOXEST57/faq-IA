from flask import Blueprint, jsonify, request
from backend.app import db # Changed to absolute import
from backend.models import FAQ # Changed to absolute import

faq_bp = Blueprint('faq', __name__, url_prefix='/api/faqs')

@faq_bp.route('/', methods=['GET'])
def get_all_faqs():
    faqs = FAQ.query.all()
    return jsonify([{'id': faq.id, 'question': faq.question, 'answer': faq.answer, 'source': faq.source, 'category': faq.category} for faq in faqs])

@faq_bp.route('/<int:faq_id>', methods=['GET'])
def get_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    return jsonify({'id': faq.id, 'question': faq.question, 'answer': faq.answer, 'source': faq.source, 'category': faq.category})

@faq_bp.route('/', methods=['POST'])
def create_faq():
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
    return jsonify(message="FAQ created successfully", id=new_faq.id), 201

@faq_bp.route('/<int:faq_id>', methods=['PUT'])
def update_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    data = request.get_json()
    
    if 'question' in data:
        faq.question = data['question']
    if 'answer' in data:
        faq.answer = data['answer']
    if 'source' in data:
        faq.source = data['source']
    if 'category' in data:
        faq.category = data['category']
        
    db.session.commit()
    return jsonify(message="FAQ updated successfully")

@faq_bp.route('/<int:faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify(message="FAQ deleted successfully"), 204
