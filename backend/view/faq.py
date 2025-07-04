from flask import Blueprint, jsonify, request
from models import db, FAQ
import json
from werkzeug.utils import secure_filename
from flask import Blueprint, jsonify
from backend.app.services.faq_service import FAQService

faq_bp = Blueprint('faq', __name__)

@faq_bp.route('/api/faq/stats', methods=['GET'])
def get_faq_stats():
    stats = FAQService.get_faq_stats()
    return jsonify(stats)

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

@faq_bp.route('/api/faq/<int:faq_id>', methods=['PUT', 'PATCH'])
def update_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    data = request.get_json()
    
    if 'question' in data:
        faq.question = data['question']
    if 'answer' in data:
        faq.answer = data['answer']
    if 'source' in data:
        faq.source = data['source']
    
    db.session.commit()
    return jsonify({
        'message': 'FAQ updated successfully',
        'faq': {
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'source': faq.source,
            'updated_at': faq.updated_at
        }
    })

@faq_bp.route('/api/faq/<int:faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify({'message': 'FAQ supprimée.'}), 204

@faq_bp.route('/api/faq/upload', methods=['POST'])
def upload_faq_json():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'File is not a JSON'}), 400
    try:
        data = json.load(file)
        if not isinstance(data, list):
            return jsonify({'error': 'JSON must be a list of FAQ objects'}), 400
        faqs = []
        for entry in data:
            question = entry.get('question')
            answer = entry.get('answer')
            source = entry.get('source', 'manuel')
            if not question or not answer:
                continue  # skip invalid entries
            faqs.append(FAQ(question=question, answer=answer, source=source))
        if not faqs:
            return jsonify({'error': 'No valid FAQ entries found in file'}), 400
        db.session.bulk_save_objects(faqs)
        db.session.commit()
        return jsonify({'message': f'{len(faqs)} FAQ(s) uploaded successfully.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
