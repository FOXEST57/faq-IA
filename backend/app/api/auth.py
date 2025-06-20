from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import validate_email, validate_password, hash_password, verify_password
from app.utils.logger import logger

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400
    
    if not validate_email(email):
        return jsonify({"msg": "Invalid email format"}), 400
    
    if not validate_password(password):
        return jsonify({"msg": "Password must be at least 8 characters with uppercase, lowercase and digits"}), 400
    
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({"msg": "Email already registered"}), 400
            
        new_user = User(
            email=email,
            password_hash=hash_password(password)
        )
        db.add(new_user)
        db.commit()
        return jsonify({"msg": "User created successfully"}), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {str(e)}")
        return jsonify({"msg": "User creation failed"}), 500
    finally:
        db.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(user.password_hash, password):
            return jsonify({"msg": "Invalid credentials"}), 401
            
        access_token = create_access_token(identity={
            'id': str(user.id),
            'email': user.email,
            'is_admin': user.is_admin
        })
        return jsonify(access_token=access_token), 200
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return jsonify({"msg": "Login failed"}), 500
    finally:
        db.close()