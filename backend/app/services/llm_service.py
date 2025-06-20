import requests
from flask import current_app
from app.utils.logger import logger

def generate_answer(question, context):
    config = current_app.config
    prompt = f"""
    [INST] <<SYS>>
    You are a helpful assistant. Answer the question using ONLY the provided context.
    If the context doesn't contain the answer, say "I don't have information about this".
    Context: {context}
    <</SYS>>
    Question: {question} [/INST]
    """
    
    try:
        response = requests.post(
            f"{config['OLLAMA_BASE_URL']}/api/generate",
            json={
                "model": config['LLM_MODEL'],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_ctx": 4096
                }
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM request failed: {str(e)}")
        return "I'm having trouble answering right now. Please try again later."