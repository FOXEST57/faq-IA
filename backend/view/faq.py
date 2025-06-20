from flask import Blueprint, jsonify, request
from models import db, FAQ

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

@faq_bp.route('/api/faq/<int:faq_id>', methods=['PUT'])
def update_faq(faq_id):
    data = request.get_json()
    faq = FAQ.query.get_or_404(faq_id)
    faq.question = data.get('question', faq.question)
    faq.answer = data.get('answer', faq.answer)
    faq.source = data.get('source', faq.source)
    db.session.commit()
    return jsonify({
        'id': faq.id,
        'question': faq.question,
        'answer': faq.answer,
        'source': faq.source,
        'created_at': str(faq.created_at) if faq.created_at else None,
        'updated_at': str(faq.updated_at) if faq.updated_at else None
    })

@faq_bp.route('/api/faq/<int:faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify({'message': 'FAQ supprimée.'}), 204
