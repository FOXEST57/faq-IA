import streamlit as st
import PyPDF2
import ollama
from io import BytesIO
import json
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import os
import re
import subprocess
import sys
import signal
import atexit
import threading
import pandas as pd
import requests
import base64

# Set page configuration
st.set_page_config(
    page_title="PDF to FAQ Generator",
    page_icon="❓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== OLLAMA SERVER MANAGEMENT =====
def is_ollama_running():
    """Check if Ollama server is running using API endpoint"""
    try:
        # More reliable check using health endpoint
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def launch_ollama_if_not_running():
    """Launch Ollama server if it is not running"""
    if not is_ollama_running():
        start_ollama_server_with_model()

def start_ollama_server_with_model():
    """Start Ollama server and ensure model is loaded"""
    try:
        # Check if server is already running
        if is_ollama_running():
            st.session_state.ollama_status = "running"
            return True
            
        st.info("Starting Ollama server...")
        
        # Start server in background
        if sys.platform == "win32":
            process = subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                ["ollama", "serve"],
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
        # Store process reference
        st.session_state.ollama_process = process
        
        # Wait for server to start with progress indicator
        with st.spinner("Waiting for Ollama to start..."):
            for _ in range(15):  # Wait up to 15 seconds
                time.sleep(1)
                if is_ollama_running():
                    st.session_state.ollama_status = "running"
                    break
            else:
                st.error("Ollama failed to start within 15 seconds")
                return False

        # Verify model availability
        try:
            models = ollama.list().get('models', [])
            model_names = [m['name'] for m in models]
            
            if st.session_state.model_name not in model_names:
                st.info(f"{st.session_state.model_name} not found, downloading now...")
                if not download_model(st.session_state.model_name):
                    return False
            return True
        except Exception as e:
            st.error(f"Model check error: {str(e)}")
            return False
                
    except Exception as e:
        st.error(f"Error starting Ollama: {str(e)}")
        return False

def stop_ollama_server():
    """Stop Ollama server if it's running"""
    if hasattr(st.session_state, 'ollama_process') and st.session_state.ollama_process:
        try:
            if sys.platform == "win32":
                st.session_state.ollama_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(st.session_state.ollama_process.pid), signal.SIGTERM)
            st.session_state.ollama_process = None
        except:
            pass

# Register cleanup function
atexit.register(stop_ollama_server)

# ===== FUNCTION DEFINITIONS =====

# Initialize ALL session state variables at the beginning
def initialize_session_state():
    if 'faqs' not in st.session_state:
        st.session_state.faqs = []
    if 'approved_faqs' not in st.session_state:
        st.session_state.approved_faqs = []
    if 'raw_output' not in st.session_state:
        st.session_state.raw_output = ""
    if 'generation_complete' not in st.session_state:
        st.session_state.generation_complete = False
    if 'run_generation' not in st.session_state:
        st.session_state.run_generation = False
    if 'ollama_status' not in st.session_state:
        st.session_state.ollama_status = "Not checked"
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'db_path' not in st.session_state:
        st.session_state.db_path = './faq.db'
    if 'model_name' not in st.session_state:
        st.session_state.model_name = 'mistral:7b-instruct-v0.3-fp16'
    if 'available_models' not in st.session_state:
        st.session_state.available_models = []
    if 'processing_time' not in st.session_state:
        st.session_state.processing_time = 0
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = ""
    if 'ollama_process' not in st.session_state:
        st.session_state.ollama_process = None
    if 'model_downloading' not in st.session_state:
        st.session_state.model_downloading = False
    if 'model_download_progress' not in st.session_state:
        st.session_state.model_download_progress = 0
    if 'editing_faq' not in st.session_state:
        st.session_state.editing_faq = None
    if 'show_delete_confirm' not in st.session_state:
        st.session_state.show_delete_confirm = False
    if 'faq_to_delete' not in st.session_state:
        st.session_state.faq_to_delete = None
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "table"  # "table" or "card"
    if 'initial_ollama_check' not in st.session_state:
        st.session_state.initial_ollama_check = False

# Function to check Ollama status and get available models
def check_ollama_status():
    try:
        models = ollama.list()
        st.session_state.available_models = [model['name'] for model in models.get('models', [])]
        st.session_state.ollama_status = "running"
        return True
    except Exception as e:
        st.session_state.ollama_status = "not_running"
        st.session_state.available_models = []
        return False

# Function to extract PDF text
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        text = ""
        for page in range(len(reader.pages)):
            page_text = reader.pages[page].extract_text()
            if page_text:
                text += page_text + "\n"
        return text[:8000]  # Limit to 8000 characters
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None

# Function to parse generated FAQs
def parse_faqs(raw_text, max_faqs=100):
    faqs = []
    pattern = r'(?:Q:|Question:|^\d+[\.\)]\s*)(.*?)\s*(?:A:|Answer:|$)(.*?)(?=(?:\n\n|\nQ:|$))'
    matches = re.findall(pattern, raw_text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    
    for match in matches[:max_faqs]:
        question = match[0].strip()
        answer = match[1].strip()
        if question and answer:
            faqs.append({
                'question': question,
                'answer': answer,
                'approved': False,
                'source': 'PDF Upload',
                'category': 'General'
            })
    return faqs

# Function to generate a single FAQ batch
def generate_faq_batch(text_chunk, model, num_faqs_per_chunk):
    prompt = f"""
    Generate exactly {num_faqs_per_chunk} FAQ questions and answers based on the following text.
    Format each FAQ strictly as: "Q: [question here]\nA: [answer here]\n\n"
    Text: {text_chunk}
    """
    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            stream=False,
            options={'temperature': 0.7}
        )
        return response['response']
    except Exception as e:
        st.error(f"Error generating FAQ batch: {e}")
        return None

# Function to save FAQs to SQLite database
def save_faqs_to_db(faqs):
    conn = None
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(st.session_state.db_path), exist_ok=True)
        
        conn = sqlite3.connect(st.session_state.db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source TEXT,
            category TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    
        for faq in faqs:
            c.execute("INSERT INTO faq (question, answer, source, category) VALUES (?, ?, ?, ?)",
                      (faq['question'], faq['answer'], faq.get('source', 'PDF Upload'), faq.get('category', 'General')))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Function to download model with progress
def download_model(model_name):
    try:
        st.session_state.model_downloading = True
        st.session_state.model_download_progress = 0
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Start download in a thread
        def download_thread():
            try:
                for progress in ollama.pull(model_name, stream=True):
                    if 'completed' in progress and 'total' in progress and progress['total'] > 0:
                        percent = progress['completed'] / progress['total']
                        st.session_state.model_download_progress = percent
                        status_text.text(f"Downloading {model_name}: {progress.get('status', '')} ({int(percent*100)}%)")
            except Exception as e:
                st.error(f"Download error: {str(e)}")
            finally:
                st.session_state.model_downloading = False
                check_ollama_status()
        
        threading.Thread(target=download_thread).start()
        
        # Update UI while downloading
        while st.session_state.model_downloading:
            progress_bar.progress(st.session_state.model_download_progress)
            time.sleep(0.1)
        
        progress_bar.empty()
        status_text.empty()
        
        if not st.session_state.model_downloading and st.session_state.model_download_progress >= 1:
            st.success(f"Model {model_name} downloaded successfully!")
            return True
        else:
            st.error("Model download failed or was cancelled")
            return False
            
    except Exception as e:
        st.error(f"Error downloading model: {str(e)}")
        return False

# ===== SESSION STATE INITIALIZATION =====
initialize_session_state()

# ===== MAIN UI CODE =====

# Modern Tailwind-inspired CSS
st.markdown("""
<style>
    :root {
        --primary: #4f46e5;
        --primary-light: #818cf8;
        --primary-dark: #3730a3;
        --secondary: #f472b6;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
        --background: #f8fafc;
        --card: #ffffff;
        --text: #1e293b;
        --text-light: #64748b;
        --border: #e2e8f0;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    body {
        background-color: var(--background);
        font-family: 'Inter', sans-serif;
        color: var(--text);
    }
    
    .stApp {
        background-color: var(--background);
    }
    
    .card {
        background: var(--card);
        border-radius: 0.75rem;
        box-shadow: var(--shadow);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
        cursor: pointer;
        border: none;
    }
    
    .btn-primary {
        background-color: var(--primary);
        color: white;
    }
    
    .btn-primary:hover {
        background-color: var(--primary-dark);
    }
    
    .btn-outline {
        background-color: transparent;
        border: 1px solid var(--border);
        color: var(--text);
    }
    
    .btn-outline:hover {
        background-color: var(--background);
    }
    
    .btn-danger {
        background-color: var(--error);
        color: white;
    }
    
    .btn-danger:hover {
        background-color: #dc2626;
    }
    
    .table-container {
        border-radius: 0.75rem;
        overflow: hidden;
        box-shadow: var(--shadow);
        margin: 1.5rem 0;
        background-color: white;
    }
    
    .stDataFrame {
        border: none !important;
    }
    
    .table-header {
        background-color: var(--primary) !important;
        color: white !important;
    }
    
    .table-row {
        transition: background-color 0.2s;
        border-bottom: 1px solid var(--border);
    }
    
    .table-row:hover {
        background-color: #f1f5f9 !important;
    }
    
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .badge-primary {
        background-color: #e0e7ff;
        color: var(--primary);
    }
    
    .badge-success {
        background-color: #d1fae5;
        color: var(--success);
    }
    
    .badge-warning {
        background-color: #fef3c7;
        color: var(--warning);
    }
    
    .empty-state {
        text-align: center;
        padding: 3rem;
        background-color: var(--card);
        border-radius: 0.75rem;
        border: 1px dashed var(--border);
    }
    
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    
    .modal-content {
        background-color: white;
        border-radius: 0.75rem;
        width: 90%;
        max-width: 600px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }
    
    .chip {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        background-color: #f1f5f9;
        color: var(--text-light);
    }
    
    .action-btn {
        padding: 0.25rem 0.5rem;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
        border: none;
        background: none;
        font-size: 0.875rem;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .action-btn:hover {
        background-color: #f1f5f9;
    }
    
    .toggle-container {
        display: flex;
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        overflow: hidden;
        width: fit-content;
        margin-bottom: 1.5rem;
    }
    
    .toggle-option {
        padding: 0.5rem 1rem;
        cursor: pointer;
        transition: all 0.2s;
        background-color: white;
        font-weight: 500;
    }
    
    .toggle-option.active {
        background-color: var(--primary);
        color: white;
    }
    
    .divider {
        height: 1px;
        background-color: var(--border);
        margin: 1.5rem 0;
    }
    
    .faq-content {
        background: #f8fafc;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    }
    
    .stButton>button {
        border-radius: 0.5rem !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# Main UI
st.title("📄 PDF to FAQ Generator")
st.markdown("Transform PDF content into FAQs using AI - Review, edit, and export knowledge base")

# Add startup check for Ollama
if not st.session_state.initial_ollama_check:
    with st.spinner("Checking Ollama status..."):
        if not is_ollama_running():
            st.warning("Ollama server not running! Starting automatically...")
            if not start_ollama_server_with_model():
                st.error("Failed to start Ollama. Please ensure Ollama is installed.")
        else:
            st.session_state.ollama_status = "running"
    st.session_state.initial_ollama_check = True

# Sidebar with status checks
with st.sidebar:
    st.subheader("System Status")
    
    # Ollama status check
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Check Ollama Status", key="check_ollama", use_container_width=True):
            check_ollama_status()
    with col2:
        if st.button("🔄", key="refresh_ollama", help="Refresh Ollama status"):
            check_ollama_status()
    
    if st.session_state.ollama_status == "running":
        st.markdown('<div class="status-box success-box">✅ Ollama server is running</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="status-box success-box">✅ Model: {st.session_state.model_name}</div>', unsafe_allow_html=True)
    elif st.session_state.ollama_status == "not_running":
        st.markdown('<div class="status-box error-box">❌ Ollama server not detected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box warning-box">⚠️ Ollama status not checked</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Configuration")
    
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", 
                                    help="Upload a PDF document to generate FAQs from")
    
    # Model selection
    if st.session_state.available_models:
        st.session_state.model_name = st.selectbox(
            "Select Model", 
            st.session_state.available_models,
            index=st.session_state.available_models.index(st.session_state.model_name) 
            if st.session_state.model_name in st.session_state.available_models else 0
        )
    else:
        st.info("No models available. Check Ollama status")
    
    num_faqs_to_generate = st.slider("Number of FAQs", min_value=3, max_value=20, value=7, 
                                     help="Number of FAQ items to generate")
    
    if st.button("Generate FAQs", use_container_width=True, type="primary", key="generate_btn"):
        if uploaded_file is None:
            st.error("Please upload a PDF file first!")
        else:
            with st.spinner("Starting Ollama server and loading model..."):
                if start_ollama_server_with_model():
                    st.session_state.run_generation = True
                    st.session_state.pdf_processed = False
                    st.session_state.generation_complete = False
                    st.session_state.faqs = []  # Clear previous FAQs
                    st.session_state.approved_faqs = []  # Clear previous approved FAQs
                    st.session_state.processing_time = 0
                else:
                    st.error("Failed to start Ollama server. Please check installation.")
    
    # Model download section
    if st.session_state.ollama_status == "running" and st.session_state.model_name not in st.session_state.available_models:
        st.warning(f"Model '{st.session_state.model_name}' not available")
        if st.button(f"Download {st.session_state.model_name}", key="download_model_btn"):
            download_model(st.session_state.model_name)
    
    st.divider()
    
    st.subheader("Approved FAQs")
    if st.session_state.approved_faqs:
        st.success(f"{len(st.session_state.approved_faqs)} FAQs approved")
        
        # Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Approved", len(st.session_state.approved_faqs))
        with col2:
            categories = len(set(faq.get('category', 'General') for faq in st.session_state.approved_faqs))
            st.metric("Categories", categories)
        
        export_data = []
        for faq in st.session_state.approved_faqs:
            export_data.append({
                "question": faq['question'], 
                "answer": faq['answer'], 
                "source": faq.get('source', 'PDF Upload'), 
                "category": faq.get('category', 'General')
            })
            
        json_data = json.dumps(export_data, indent=2)
        st.download_button(
            label="Export as JSON",
            data=json_data,
            file_name="approved_faqs.json",
            mime="application/json",
            use_container_width=True
        )
        
        if st.button("Save to Database", use_container_width=True, key="save_to_db_btn"):
            if save_faqs_to_db(st.session_state.approved_faqs):
                st.success("Approved FAQs saved to database!")
                st.session_state.approved_faqs = []  # Clear approved after saving
                time.sleep(1)
                st.rerun()
                
        if st.button("Clear Approved", use_container_width=True, key="clear_approved_btn", 
                    help="Remove all approved FAQs without saving"):
            st.session_state.approved_faqs = []
            st.success("Approved FAQs cleared!")
            time.sleep(1)
            st.rerun()
    else:
        st.info("No approved FAQs yet")
        
    st.divider()
    
    if st.checkbox("Show raw model output", key="show_raw_output"):
        st.subheader("Raw Model Output")
        st.text_area("", value=st.session_state.raw_output, height=250, label_visibility="collapsed")

# Main content area
# Generate FAQs when triggered
if st.session_state.run_generation and uploaded_file and not st.session_state.pdf_processed:
    start_time = time.time()
    
    with st.spinner("📄 Extracting text from PDF..."):
        pdf_text = extract_text_from_pdf(uploaded_file)
        if pdf_text is None:
            st.error("Failed to extract text from PDF. Please try a different file.")
            st.session_state.run_generation = False
        else:
            st.session_state.pdf_text = pdf_text
    
    if st.session_state.get('pdf_text'):
        total_faqs_to_generate = num_faqs_to_generate
        num_workers = min(total_faqs_to_generate, 4)  # Reduce parallel workers
        
        # Distribute FAQs among workers
        faqs_per_worker = [total_faqs_to_generate // num_workers] * num_workers
        for i in range(total_faqs_to_generate % num_workers):
            faqs_per_worker[i] += 1

        generated_faqs_list = []
        raw_outputs = []
        futures = []

        with st.spinner(f"🧠 Generating {total_faqs_to_generate} FAQs using {st.session_state.model_name}..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                for i, num_faqs in enumerate(faqs_per_worker):
                    if num_faqs > 0:
                        future = executor.submit(
                            generate_faq_batch, 
                            st.session_state.pdf_text, 
                            st.session_state.model_name, 
                            num_faqs
                        )
                        futures.append(future)
                
                for i, future in enumerate(futures):
                    progress = (i + 1) / len(futures)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing batch {i+1}/{len(futures)}...")
                    
                    faq_output = future.result()
                    if faq_output:
                        raw_outputs.append(faq_output)
                        parsed_faqs = parse_faqs(faq_output, num_faqs)
                        generated_faqs_list.extend(parsed_faqs)

        # Trim to the exact number of requested FAQs
        st.session_state.faqs = generated_faqs_list[:total_faqs_to_generate]

        if st.session_state.faqs:
            st.session_state.raw_output = "\n---\n".join(raw_outputs)
            st.session_state.generation_complete = True
            st.session_state.pdf_processed = True
            st.session_state.processing_time = time.time() - start_time
            st.success(f"✅ {len(st.session_state.faqs)} FAQs generated in {st.session_state.processing_time:.1f} seconds!")
        else:
            st.error("Failed to generate FAQs. Please check the model and try again.")
            st.session_state.run_generation = False

# Display question and answer FAQs
elif st.session_state.generation_complete and st.session_state.faqs:
    st.divider()
    
    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Generated FAQs", len(st.session_state.faqs))
    with col2:
        st.metric("Approved FAQs", len(st.session_state.approved_faqs))
    with col3:
        st.metric("Processing Time", f"{st.session_state.processing_time:.1f} sec")
    
    st.subheader("Manage Generated FAQs")
    
    # View mode toggle
    st.markdown("""
    <div class="toggle-container">
        <div class="toggle-option %s" onclick="setViewMode('table')">Table View</div>
        <div class="toggle-option %s" onclick="setViewMode('card')">Card View</div>
    </div>
    """ % (
        "active" if st.session_state.view_mode == "table" else "",
        "active" if st.session_state.view_mode == "card" else ""
    ), unsafe_allow_html=True)
    
    st.markdown("""
    <script>
        function setViewMode(mode) {
            Streamlit.setComponentValue("view_mode_" + mode);
        }
    </script>
    """, unsafe_allow_html=True)
    
    if st.button("Table View", key="view_mode_table", use_container_width=True):
        st.session_state.view_mode = "table"
        st.rerun()
        
    if st.button("Card View", key="view_mode_card", use_container_width=True):
        st.session_state.view_mode = "card"
        st.rerun()
    
    # Table view
    if st.session_state.view_mode == "table":
        st.markdown('<div class="table-container">', unsafe_allow_html=True)
        
        # Table headers
        headers = ["Select", "ID", "Question", "Answer", "Category", "Status", "Actions"]
        cols = st.columns([0.5, 0.5, 2, 2, 1, 1, 1.5])
        
        for i, header in enumerate(headers):
            cols[i].markdown(f"**{header}**")
        
        # Table rows
        for i, faq in enumerate(st.session_state.faqs):
            cols = st.columns([0.5, 0.5, 2, 2, 1, 1, 1.5])
            
            # Checkbox for selection
            with cols[0]:
                selected = st.checkbox("", key=f"select_{i}", label_visibility="collapsed")
            
            # ID
            cols[1].write(i+1)
            
            # Question preview
            question_preview = faq['question'][:80] + "..." if len(faq['question']) > 80 else faq['question']
            cols[2].write(question_preview)
            
            # Answer preview
            answer_preview = faq['answer'][:80] + "..." if len(faq['answer']) > 80 else faq['answer']
            cols[3].write(answer_preview)
            
            # Category
            cols[4].write(faq['category'])
            
            # Status badge
            status_badge = f'<span class="badge {"badge-success" if faq["approved"] else "badge-warning"}">{"Approved" if faq["approved"] else "Pending"}</span>'
            cols[5].markdown(status_badge, unsafe_allow_html=True)
            
            # Action buttons
            with cols[6]:
                col1, col2, col3 = st.columns([1,1,1])
                with col1:
                    if st.button("✏️", key=f"edit_{i}", help="Edit FAQ", use_container_width=True):
                        st.session_state.editing_faq = i
                with col2:
                    if st.button("✅", key=f"approve_{i}", help="Approve FAQ", 
                                type="primary" if faq['approved'] else "secondary", use_container_width=True):
                        st.session_state.faqs[i]['approved'] = not st.session_state.faqs[i]['approved']
                        st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"delete_{i}", help="Delete FAQ", type="secondary", use_container_width=True):
                        st.session_state.show_delete_confirm = True
                        st.session_state.faq_to_delete = i
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Bulk actions
        st.markdown("---")
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            if st.button("Approve Selected", key="bulk_approve", use_container_width=True):
                for i, faq in enumerate(st.session_state.faqs):
                    if st.session_state.get(f"select_{i}", False):
                        st.session_state.faqs[i]['approved'] = True
                st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
                st.rerun()
        with col2:
            if st.button("Delete Selected", key="bulk_delete", type="secondary", use_container_width=True):
                st.session_state.faqs = [f for i, f in enumerate(st.session_state.faqs) 
                                        if not st.session_state.get(f"select_{i}", False)]
                st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
                st.rerun()
        with col3:
            if st.button("Export All to JSON", key="export_all", use_container_width=True):
                export_data = [{
                    "question": f['question'], 
                    "answer": f['answer'], 
                    "source": f.get('source', 'PDF Upload'), 
                    "category": f.get('category', 'General')
                } for f in st.session_state.faqs]
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name="all_faqs.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    # Card view
    else:
        for i, faq in enumerate(st.session_state.faqs):
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3>❓ Question {i+1}</h3>
                        <div>
                            <span class="badge {"badge-success" if faq["approved"] else "badge-warning"}">
                                {"Approved" if faq["approved"] else "Pending"}
                            </span>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <strong>Question:</strong>
                        <div class="faq-content">
                            {faq['question']}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <strong>Answer:</strong>
                        <div class="faq-content">
                            {faq['answer']}
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                        <div>
                            <span class="chip">Category: {faq['category']}</span>
                            <span class="chip">Source: {faq['source']}</span>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="action-btn" onclick="editFaq({i})">✏️ Edit</button>
                            <button class="action-btn" onclick="toggleApprove({i})">{"✅ Approved" if faq['approved'] else "✅ Approve"}</button>
                            <button class="action-btn" onclick="deleteFaq({i})">🗑️ Delete</button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("""
        <script>
            function editFaq(index) {
                Streamlit.setComponentValue("edit_faq_" + index);
            }
            function toggleApprove(index) {
                Streamlit.setComponentValue("approve_faq_" + index);
            }
            function deleteFaq(index) {
                Streamlit.setComponentValue("delete_faq_" + index);
            }
        </script>
        """, unsafe_allow_html=True)
        
        # Handle card actions
        for i in range(len(st.session_state.faqs)):
            if st.button(f"edit_faq_{i}", key=f"card_edit_{i}", disabled=True, label_visibility="hidden"):
                st.session_state.editing_faq = i
            if st.button(f"approve_faq_{i}", key=f"card_approve_{i}", disabled=True, label_visibility="hidden"):
                st.session_state.faqs[i]['approved'] = not st.session_state.faqs[i]['approved']
                st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
                st.rerun()
            if st.button(f"delete_faq_{i}", key=f"card_delete_{i}", disabled=True, label_visibility="hidden"):
                st.session_state.show_delete_confirm = True
                st.session_state.faq_to_delete = i
    
    # Edit FAQ modal
    if st.session_state.editing_faq is not None:
        faq_index = st.session_state.editing_faq
        faq = st.session_state.faqs[faq_index]
        
        st.markdown(f"""
        <div class="modal">
            <div class="modal-content">
                <div style="padding: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3>Edit FAQ</h3>
                        <button onclick="closeModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label><strong>Question:</strong></label>
                        <textarea id="edit-question" style="width: 100%; min-height: 100px; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid var(--border); margin-top: 0.5rem;">{faq['question']}</textarea>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label><strong>Answer:</strong></label>
                        <textarea id="edit-answer" style="width: 100%; min-height: 150px; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid var(--border); margin-top: 0.5rem;">{faq['answer']}</textarea>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                        <div>
                            <label><strong>Category:</strong></label>
                            <input id="edit-category" type="text" value="{faq['category']}" style="width: 100%; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid var(--border); margin-top: 0.5rem;">
                        </div>
                        <div>
                            <label><strong>Source:</strong></label>
                            <input id="edit-source" type="text" value="{faq['source']}" style="width: 100%; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid var(--border); margin-top: 0.5rem;">
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
                        <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
                        <button class="btn btn-primary" onclick="saveChanges({faq_index})">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function closeModal() {{
                Streamlit.setComponentValue("close_edit_modal");
            }}
            function saveChanges(index) {{
                const question = document.getElementById("edit-question").value;
                const answer = document.getElementById("edit-answer").value;
                const category = document.getElementById("edit-category").value;
                const source = document.getElementById("edit-source").value;
                
                // Encode values for Streamlit
                const encodedQuestion = btoa(unescape(encodeURIComponent(question)));
                const encodedAnswer = btoa(unescape(encodeURIComponent(answer)));
                const encodedCategory = btoa(unescape(encodeURIComponent(category)));
                const encodedSource = btoa(unescape(encodeURIComponent(source)));
                
                Streamlit.setComponentValue(`save_faq_${{index}}_${{encodedQuestion}}_${{encodedAnswer}}_${{encodedCategory}}_${{encodedSource}}`);
            }}
        </script>
        """, unsafe_allow_html=True)
        
        if st.button("close_edit_modal", key="close_edit_modal", disabled=True, label_visibility="hidden"):
            st.session_state.editing_faq = None
            st.rerun()
            
        # Handle save action
        save_key = f"save_faq_{faq_index}"
        if save_key in st.session_state:
            # Extract values from the key
            parts = st.session_state[save_key].split("_")
            question = base64.b64decode(parts[3]).decode('utf-8')
            answer = base64.b64decode(parts[4]).decode('utf-8')
            category = base64.b64decode(parts[5]).decode('utf-8')
            source = base64.b64decode(parts[6]).decode('utf-8')
            
            # Update FAQ
            st.session_state.faqs[faq_index]['question'] = question
            st.session_state.faqs[faq_index]['answer'] = answer
            st.session_state.faqs[faq_index]['category'] = category
            st.session_state.faqs[faq_index]['source'] = source
            
            st.session_state.editing_faq = None
            st.success("FAQ updated successfully!")
            time.sleep(1)
            st.rerun()
    
    # Delete confirmation modal
    if st.session_state.show_delete_confirm:
        faq_index = st.session_state.faq_to_delete
        faq = st.session_state.faqs[faq_index]
        st.markdown(f"""
        <div class="modal">
            <div class="modal-content">
                <div style="padding: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3>Confirm Deletion</h3>
                        <button onclick="closeDeleteModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    
                    <p>Are you sure you want to delete this FAQ?</p>
                    <div style="background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; margin: 1.5rem 0;">
                        <strong>Question:</strong>
                        <p>{faq['question'][:100]}{'...' if len(faq['question']) > 100 else ''}</p>
                    </div>
                    
                    <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
                        <button class="btn btn-outline" onclick="closeDeleteModal()">Cancel</button>
                        <button class="btn btn-danger" onclick="confirmDelete()">Delete FAQ</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function closeDeleteModal() {{
                Streamlit.setComponentValue("close_delete_modal");
            }}
            function confirmDelete() {{
                Streamlit.setComponentValue("confirm_delete");
            }}
        </script>
        """, unsafe_allow_html=True)
        
        if st.button("close_delete_modal", key="close_delete_modal", disabled=True, label_visibility="hidden"):
            st.session_state.show_delete_confirm = False
            st.session_state.faq_to_delete = None
            st.rerun()
            
        if st.button("confirm_delete", key="confirm_delete", disabled=True, label_visibility="hidden"):
            # Delete the FAQ
            del st.session_state.faqs[faq_index]
            st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
            st.session_state.show_delete_confirm = False
            st.session_state.faq_to_delete = None
            st.success("FAQ deleted successfully!")
            time.sleep(1)
            st.rerun()

# Show empty state if no FAQs
elif not st.session_state.run_generation:
    with st.container():
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📚</div>
            <h3>PDF to FAQ Generator</h3>
            <p>Upload a PDF document and generate FAQs using AI</p>
            <p class='text-muted'>Get started by uploading a PDF and configuring your FAQ settings</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Features grid
        st.subheader("How It Works")
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container():
                st.markdown("""
                <div class='card'>
                    <h4>1. Upload PDF</h4>
                    <p class='text-muted'>Upload any PDF document containing information you want to convert to FAQs</p>
                </div>
                """, unsafe_allow_html=True)
        with col2:
            with st.container():
                st.markdown("""
                <div class='card'>
                    <h4>2. Generate FAQs</h4>
                    <p class='text-muted'>AI analyzes your document and generates relevant question-answer pairs</p>
                </div>
                """, unsafe_allow_html=True)
        with col3:
            with st.container():
                st.markdown("""
                <div class='card'>
                    <h4>3. Review & Export</h4>
                    <p class='text-muted'>Edit, approve, and export your FAQs as JSON or save to database</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Troubleshooting section
        with st.expander("Troubleshooting Guide", expanded=False):
            st.markdown("""
            **If the application isn't working, try these steps:**
            
            1. **Verify Ollama Installation**:
               - In a terminal, run:
            """)
            
            st.markdown("""
            ```bash
            ollama list
            ```
            """)
            
            st.markdown("""
            2. **Install Missing Model**:
               - If needed, run:
            """)
            
            st.markdown("""
            ```bash
            ollama pull mistral:7b-instruct-v0.3-fp16
            ```
            """)
            
            st.markdown("""
            3. **Check System Requirements**:
               - Ensure you have at least 8GB RAM available
               - The model requires ~4.5GB of memory
            
            4. **Test Ollama API**:
               - Run this in a Python environment:
            """)
            
            st.markdown("""
            ```python
            import ollama
            response = ollama.generate(model='mistral', 
                                     prompt='Why is the sky blue?')
            print(response['response'])
            ```
            """)

# Footer
st.divider()
st.caption("PDF to FAQ Generator | Powered by Ollama | Made with Streamlit")
