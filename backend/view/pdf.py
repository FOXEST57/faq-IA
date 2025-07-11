from flask import Blueprint, request, jsonify
import PyPDF2
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from backend.app.services.ollama_service import OllamaService # Changed to absolute import

pdf_bp = Blueprint('pdf', __name__, url_prefix='/api/pdf')
ollama_service = OllamaService() # Initialize OllamaService

def extract_text_from_pdf(uploaded_file_stream):
    try:
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file_stream.read()))
        text = ""
        for page in range(len(reader.pages)):
            page_text = reader.pages[page].extract_text()
            if page_text:
                text += page_text + "\n"
        return text[:6000]  # Limit to 6000 characters
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

@pdf_bp.route('/upload-and-generate', methods=['POST'])
def upload_and_generate_faqs():
    if 'pdf_file' not in request.files:
        return jsonify(error="No PDF file provided"), 400
    
    pdf_file = request.files['pdf_file']
    num_faqs_to_generate = int(request.form.get('num_faqs', 5))

    pdf_text = extract_text_from_pdf(pdf_file)
    if pdf_text is None:
        return jsonify(error="Failed to extract text from PDF"), 500

    if not ollama_service.check_ollama_status():
        return jsonify(error="Ollama server is not running"), 503

    generated_faqs_list = []
    raw_outputs = []
    futures = []

    num_workers = min(num_faqs_to_generate, 5) # Cap workers
    faqs_per_worker = [num_faqs_to_generate // num_workers] * num_workers
    for i in range(num_faqs_to_generate % num_workers):
        faqs_per_worker[i] += 1

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for num_faqs in faqs_per_worker:
            if num_faqs > 0:
                future = executor.submit(ollama_service.generate_faq_batch, pdf_text, num_faqs)
                futures.append(future)
        
        for future in futures:
            faq_output = future.result()
            if faq_output:
                raw_outputs.append(faq_output)
                parsed_faqs = parse_faqs(faq_output, 100) # Parse up to 100, will be trimmed later
                generated_faqs_list.extend(parsed_faqs)

    final_faqs = generated_faqs_list[:num_faqs_to_generate]

    if final_faqs:
        return jsonify({
            "message": "FAQs generated successfully",
            "faqs": final_faqs,
            "raw_output": "\n---\n".join(raw_outputs)
        })
    else:
        return jsonify(error="Failed to generate FAQs"), 500

def parse_faqs(faq_text, num_faqs_expected):
    entries = []
    current_q = None
    current_a = None
    
    lines = faq_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('Q:'):
            if current_q is not None and current_a is not None:
                entries.append({"question": current_q, "answer": current_a, "approved": False})
            current_q = line[2:].strip()
            current_a = None
        elif line.startswith('A:'):
            current_a = line[2:].strip()
    
    if current_q and current_a:
        entries.append({"question": current_q, "answer": current_a, "approved": False})
    
    return entries[:num_faqs_expected]
