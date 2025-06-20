import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename):
    # Custom implementation to avoid Werkzeug dependency issues
    filename = os.path.basename(filename)
    filename = filename.strip().replace(' ', '_')
    keep_chars = ('-', '_', '.')
    return ''.join(c for c in filename if c.isalnum() or c in keep_chars)