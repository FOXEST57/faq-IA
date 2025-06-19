from flask import Blueprint, jsonify, request
from backend.models import db, FAQ

faq_bp = Blueprint('faq', __name__)

@faq_bp.route('/api/faq', methods=['GET'])
def get_faqs():
    faqs = FAQ.query.all()
    return jsonify([
        {
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'source': faq.source,
            'created_at': str(faq.created_at) if faq.created_at else None,
            'updated_at': str(faq.updated_at) if faq.updated_at else None
        } for faq in faqs
    ])

@faq_bp.route('/api/faq', methods=['POST'])
def create_faq():
    data = request.get_json()
    faq = FAQ(
        question=data.get('question'),
        answer=data.get('answer'),
        source=data.get('source', 'manuel')
    )
    db.session.add(faq)
    db.session.commit()
    return jsonify({
        'id': faq.id,
        'question': faq.question,
        'answer': faq.answer,
        'source': faq.source,
        'created_at': str(faq.created_at) if faq.created_at else None,
        'updated_at': str(faq.updated_at) if faq.updated_at else None
    }), 201

@faq_bp.route('/api/faq/<int:faq_id>', methods=['GET'])
def get_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    return jsonify({
        'id': faq.id,
        'question': faq.question,
        'answer': faq.answer,
        'source': faq.source,
        'created_at': str(faq.created_at) if faq.created_at else None,
        'updated_at': str(faq.updated_at) if faq.updated_at else None
    })
