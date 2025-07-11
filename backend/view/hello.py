from flask import Blueprint, jsonify

hello_bp = Blueprint('hello', __name__, url_prefix='/api/hello')

@hello_bp.route('/')
def hello_world():
    return jsonify(message="Hello from the backend API!")

