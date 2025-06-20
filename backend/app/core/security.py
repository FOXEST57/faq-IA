import re
import uuid
import hashlib
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from functools import wraps

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

def hash_password(password):
    salt = uuid.uuid4().hex
    hashed = hashlib.sha512((password + salt).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"

def verify_password(hashed_password, user_password):
    salt, hashed = hashed_password.split('$')
    return hashed == hashlib.sha512((user_password + salt).encode('utf-8')).hexdigest()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        identity = get_jwt_identity()
        if not identity.get('is_admin', False):
            return jsonify({"msg": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper