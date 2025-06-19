from flask import Blueprint, jsonify
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
