from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.core.cache import cache_response
from app.db.session import SessionLocal
from app.db.models import Question, Answer
from app.services.llm_service import generate_answer
from app.utils.logger import logger
import uuid
import json
from flask import render_template
# Assuming you have a way to get FAQs, e.g., from your db.models
# from app.db.models import FAQ

faq_bp = Blueprint('faq', __name__)

@faq_bp.route('/ask', methods=['POST'])
@jwt_required()
@cache_response(ttl=3600)
def ask_question():
    # Get vector store instance
    vector_store = current_app.vector_store
    data = request.get_json()
    question_text = data.get('question')
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    if not question_text:
        return jsonify({"msg": "Missing question"}), 400
    
    # Retrieve relevant context
    search_results = vector_store.search(question_text, k=5)
    context_parts = []
    
    db = SessionLocal()
    try:
        # Get document content for context
        for result in search_results:
            doc = db.query(Document).get(uuid.UUID(result['id']))
            if doc:
                doc.usage_count += 1
                context_parts.append(doc.content)
        
        # Generate answer
        context = "\n\n".join(context_parts)
        answer_text = generate_answer(question_text, context)
        
        # Get current user
        current_user = get_jwt_identity()
        user_id = uuid.UUID(current_user['id'])
        
        # Save to database
        new_question = Question(
            content=question_text,
            session_id=session_id,
            user_id=user_id
        )
        db.add(new_question)
        db.commit()
        db.refresh(new_question)
        
        new_answer = Answer(
            content=answer_text,
            question_id=new_question.id,
            model_version=current_app.config['LLM_MODEL'],
            sources=json.dumps([{'id': r['id'], 'score': r['score']} for r in search_results])
        )
        db.add(new_answer)
        db.commit()
        
        return jsonify({
            "answer": answer_text,
            "sources": [{'id': r['id'], 'score': r['score']} for r in search_results],
            "session_id": session_id,
            "answer_id": str(new_answer.id)
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Question processing failed: {str(e)}")
        return jsonify({"msg": "Failed to process question"}), 500
    finally:
        db.close()

@faq_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    data = request.get_json()
    answer_id = data.get('answer_id')
    rating = data.get('rating')
    
    if not answer_id or rating is None:
        return jsonify({"msg": "Missing answer_id or rating"}), 400
    
    try:
        answer_uuid = uuid.UUID(answer_id)
    except ValueError:
        return jsonify({"msg": "Invalid answer ID format"}), 400
    
    db = SessionLocal()
    try:
        answer = db.query(Answer).get(answer_uuid)
        if not answer:
            return jsonify({"msg": "Answer not found"}), 404
            
        answer.rating = rating
        db.commit()
        return jsonify({"msg": "Feedback submitted"}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"Feedback submission failed: {str(e)}")
        return jsonify({"msg": "Failed to submit feedback"}), 500
    finally:
        db.close()


@faq_bp.route('/faqs') # Or wherever your FAQ route is defined
def list_faqs():
    # Replace this with your actual logic to fetch FAQs
    # For example: faqs = FAQ.query.all()
    faqs_list = [
        {'question': 'What is this project?', 'answer': 'It is a backend application.'},
        {'question': 'How does it work?', 'answer': 'Using Flask, SQLAlchemy, etc.'}
    ]
    return render_template('index.html', faqs=faqs_list)