import streamlit as st
import PyPDF2
import ollama
from io import BytesIO
import json
import time

# Set page configuration
st.set_page_config(
    page_title="PDF to FAQ Generator",
    page_icon="❓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
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
if 'display_counter' not in st.session_state:
    st.session_state.display_counter = 0
if 'pdf_processed' not in st.session_state:
    st.session_state.pdf_processed = False

# Custom CSS for minimal UI
st.markdown("""
<style>
    :root {
        --primary-light: #818cf8;
        --secondary: #f472b6;
        --background: #202129;
        --card: #404254;
        --text: #f5f7fa;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
    }
    
    body {
        background-color: var(--background);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .stApp {
        
    }
    
    .card {
        background: var(--card);
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid #e5e7eb;
    }
    
    .stButton>button {
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        transition: all 0.3s !important;
    }
    
    .stButton>button:focus {
        box-shadow: 0 0 0 0.2rem rgba(79, 70, 229, 0.25) !important;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--secondary)) !important;
    }
    
    .status-box {
        padding: 15px;
        border-radius: 12px;
        margin: 15px 0;
        font-weight: 500;
    }
    
    .success-box {
        background: rgba(16, 185, 129, 0.1);
        border-left: 4px solid var(--success);
    }
    
    .error-box {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid var(--error);
    }
    
    .warning-box {
        background: rgba(245, 158, 11, 0.1);
        border-left: 4px solid var(--warning);
    }
    
    .faq-container {
        padding: 20px;
        margin-bottom: 25px;
        border-radius: 12px;
        background: var(--background);
        color: var(--text);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Main UI
st.title("📄 PDF to FAQ Generator")
st.markdown("Upload PDFs and generate FAQs using Ollama's Mistral model")

# Function to check Ollama status
def check_ollama_status():
    try:
        ollama.list()
        st.session_state.ollama_status = "running"
        return True
    except:
        st.session_state.ollama_status = "not_running"
        return False

# Sidebar with status checks
with st.sidebar:
    st.subheader("System Status")
    
    # Ollama status check
    if st.button("Check Ollama Status"):
        check_ollama_status()
    
    if st.session_state.ollama_status == "running":
        st.markdown('<div class="status-box success-box">✅ Ollama server is running</div>', unsafe_allow_html=True)
    elif st.session_state.ollama_status == "not_running":
        st.markdown('<div class="status-box error-box">❌ Ollama server not detected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box warning-box">⚠️ Ollama status not checked</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Configuration")
    
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", help="Upload a PDF document to generate FAQs from")
    num_faqs_to_generate = st.slider("Number of FAQs", min_value=3, max_value=20, value=5, 
                                     help="Number of FAQ items to generate")
    
    if st.button("Generate FAQs", use_container_width=True, type="primary", key="generate_btn"):
        if uploaded_file is None:
            st.error("Please upload a PDF file first!")
        elif not check_ollama_status():
            st.error("Ollama server is not running. Please start it first.")
        else:
            st.session_state.run_generation = True
            st.session_state.pdf_processed = False
            st.session_state.generation_complete = False
            st.session_state.display_counter = 0
    
    st.divider()
    
    st.subheader("Approved FAQs")
    if st.session_state.approved_faqs:
        st.success(f"{len(st.session_state.approved_faqs)} FAQs approved")
        export_data = [{"question": faq['question'], "answer": faq['answer']} for faq in st.session_state.approved_faqs]
        json_data = json.dumps(export_data, indent=2)
        st.download_button(
            label="Export as JSON",
            data=json_data,
            file_name="approved_faqs.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.info("No approved FAQs yet")
        
    st.divider()
    
    if st.checkbox("Show raw model output"):
        st.subheader("Raw Model Output")
        st.text_area("", value=st.session_state.raw_output, height=250, label_visibility="collapsed")

# Function to extract PDF text
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        text = ""
        for page in range(len(reader.pages)):
            page_text = reader.pages[page].extract_text()
            if page_text:
                text += page_text + "\n"
        return text[:6000]  # Limit to 6000 characters
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None

# Function to generate FAQs
def generate_faqs(text, num_faqs):
    prompt = f"""
    Generate exactly {num_faqs} FAQ questions and answers based on the following text.
    Format each FAQ strictly as: "Q: question here\nA: answer here\n\n"
    Text: {text}
    """
    
    try:
        response = ollama.generate(
            model='mistral:7b-instruct-v0.3-fp16',
            prompt=prompt,
            options={'temperature': 0.6, 'num_predict': 2000}
        )
        return response['response']
    except Exception as e:
        st.error(f"Error generating FAQs: {str(e)}")
        return None

# Function to parse generated FAQ text
def parse_faqs(faq_text, num_faqs):
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
    
    return entries[:num_faqs]

# Generate FAQs when triggered
if st.session_state.run_generation and uploaded_file and not st.session_state.pdf_processed:
    with st.spinner("📄 Extracting text from PDF..."):
        pdf_text = extract_text_from_pdf(uploaded_file)
        if pdf_text is None:
            st.error("Failed to extract text from PDF. Please try a different file.")
            st.session_state.run_generation = False
        else:
            st.session_state.pdf_text = pdf_text
    
    if st.session_state.get('pdf_text'):
        with st.spinner(f"🧠 Generating {num_faqs_to_generate} FAQs..."):
            faq_output = generate_faqs(st.session_state.pdf_text, num_faqs_to_generate)
        
        if faq_output:
            st.session_state.raw_output = faq_output
            st.session_state.faqs = parse_faqs(faq_output, num_faqs_to_generate)
            st.session_state.generation_complete = True
            st.success("✅ FAQs generated successfully!")
            st.session_state.pdf_processed = True
        else:
            st.error("Failed to generate FAQs. Please check the model and try again.")
            st.session_state.run_generation = False

# Retrieve FAQs from database 'faq.db' from table 'faq'
def get_faqs():
    conn = sqlite3.connect('faq.db')
    c = conn.cursor()
    c.execute("SELECT * FROM faq")
    faqs = c.fetchall()
    conn.close()
    return faqs

# Add function to delete FAQ from database 'faq.db' from table 'faq'
def delete_faq(faq_id):
    conn = sqlite3.connect('faq.db')
    c = conn.cursor()
    c.execute("DELETE FROM faq WHERE id=?", (faq_id,))
    conn.commit()
    conn.close()

# Add function to approve FAQ in database 'faq.db' from table 'faq'
def approve_faq(faq_id):
    conn = sqlite3.connect('faq.db')
    c = conn.cursor()
    c.execute("UPDATE faq SET approved=1 WHERE id=?", (faq_id,))
    conn.commit()
    conn.close()



# Display question and answer FAQs stored in database 'faq.db' from table 'faq'
def display_faq(faq):
    st.markdown(f"#### ❓ Question {faq['question']}")
    st.markdown(f"#### 💬 Answer {faq['answer']}")
    st.divider()
    st.button("Delete", key=f"delete_{faq['id']}", type="secondary")
    st.button("Edit", key=f"edit_{faq['id']}", type="primary")
    # Edit button functionality
    if st.button("Edit", key=f"edit_{faq['id']}"):
        st.session_state.edit_mode = True
        st.session_state.editing_faq = faq
        st.session_state.editing_faq['question'] = faq['question']
        st.session_state.editing_faq['answer'] = faq['answer']
        st.session_state.editing_faq['id'] = faq['id']
        st.rerun()
    # Delete button functionality
    if st.button("Delete", key=f"delete_{faq['id']}"):
        with st.spinner("Deleting FAQ..."):
            delete_faq(faq['id'])
            st.session_state.faqs = [f for f in st.session_state.faqs if f['id'] != faq['id']]
            st.session_state.approved_faqs = [f for f in st.session_state.approved_faqs if f['id'] != faq['id']]
            st.success("FAQ deleted successfully!")
            st.session_state.display_counter -= 1
            st.rerun()

# Display FAQs
if st.session_state.generation_complete and st.session_state.faqs:
    st.divider()
    st.subheader("Review and Approve FAQs")
    
    # Progress display
    progress = min(1.0, (st.session_state.display_counter + 1) / len(st.session_state.faqs))
    progress_bar = st.progress(progress)
    
    # Display FAQs incrementally
    for i, faq in enumerate(st.session_state.faqs):
        if i <= st.session_state.display_counter:
            with st.container():
                st.markdown(f"#### ❓ Question {i+1}")
                edited_q = st.text_area(
                    "Question:", 
                    value=faq['question'], 
                    key=f"q_{i}",
                    height=100
                )
                st.session_state.faqs[i]['question'] = edited_q
                
                st.markdown(f"#### 💬 Answer")
                edited_a = st.text_area(
                    "Answer:", 
                    value=faq['answer'], 
                    key=f"a_{i}",
                    height=150
                )
                st.session_state.faqs[i]['answer'] = edited_a
                
                # Approval button
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button(
                        "✅ Approved" if faq['approved'] else "Approve",
                        key=f"approve_{i}",
                        type="primary" if faq['approved'] else "secondary"
                    ):
                        st.session_state.faqs[i]['approved'] = not st.session_state.faqs[i]['approved']
                        st.session_state.approved_faqs = [f for f in st.session_state.faqs if f['approved']]
                with col2:
                    if st.session_state.faqs[i]['approved']:
                        st.success("This FAQ has been approved")
                    else:
                        st.warning("Pending approval")
                
                st.divider()
    
    # Show "Load More" button if not all FAQs are displayed
    if st.session_state.display_counter < len(st.session_state.faqs) - 1:
        if st.button("Load Next FAQ", type="primary"):
            st.session_state.display_counter += 1
            st.rerun()
    else:
        st.success("All FAQs loaded!")

# Show empty state if no FAQs
elif not st.session_state.run_generation:
    with st.container():
        st.markdown("""
        <div style='text-align: center; padding: 50px 20px;'>
            <h3>📚 Get Started with PDF FAQ Generator</h3>
            <p>Upload a PDF document and click "Generate FAQs" to create question-answer pairs</p>
            <div style='font-size: 60px; margin: 30px 0;'>❓</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Troubleshooting section
        with st.expander("Troubleshooting Guide", expanded=True):
            st.markdown("""
            **If the application isn't working, try these steps:**
            
            1. **Start Ollama Server**:
               - Open a terminal and run:
                 ```
                 ollama serve
                 ```
               - Keep this terminal open while using the app
            
            2. **Verify Ollama Installation**:
               - In a new terminal, run:
                 ```
                 ollama list
                 ```
               - You should see `mistral:7b-instruct-v0.3-fp16` in the list
            
            3. **Install Missing Model**:
               - If the model is missing, run:
                 ```
                 ollama pull mistral:7b-instruct-v0.3-fp16
                 ```
            
            4. **Check System Requirements**:
               - Ensure you have at least 8GB RAM available
               - The model requires ~4.5GB of memory
            
            5. **Test Ollama API**:
               - Run this in a Python environment:
                 ```python
                 import ollama
                 response = ollama.generate(model='mistral:7b-instruct-v0.3-fp16', 
                                          prompt='Why is the sky blue?')
                 print(response['response'])
                 ```
            """)

# Approved FAQs Section
if st.session_state.approved_faqs:
    st.divider()
    st.subheader("🌟 Approved FAQs")
    
    for i, faq in enumerate(st.session_state.approved_faqs):
        with st.expander(f"Q{i+1}: {faq['question']}", expanded=False):
            st.write(faq['answer'])

# Footer
st.divider()
st.caption("PDF to FAQ Generator | Powered by Ollama | Made with Streamlit")