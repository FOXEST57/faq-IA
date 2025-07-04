import requests
import json
import logging
from typing import List, Dict, Optional
import fitz  # PyMuPDF
import os

class OllamaRAGService:
    """Service pour l'intégration Ollama et le système RAG"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger(__name__)

        # Vérifier si le modèle existe, sinon utiliser un modèle de fallback
        available_models = self.get_available_models()
        if self.model not in available_models:
            self.logger.warning(f"Modèle {self.model} non disponible")
            # Essayer des modèles plus petits
            fallback_models = ["llama3.2:1b", "llama3.1", "llama3", "gemma:2b", "phi"]
            for fallback in fallback_models:
                if fallback in available_models:
                    self.model = fallback
                    self.logger.info(f"Utilisation du modèle de fallback: {fallback}")
                    break
            else:
                self.logger.error("Aucun modèle compatible trouvé")

    def check_ollama_connection(self) -> bool:
        """Vérifie si Ollama est accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Erreur de connexion à Ollama: {e}")
            return False

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrait le texte d'un fichier PDF"""
        try:
            text = ""
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
            return text.strip()
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction du PDF {pdf_path}: {e}")
            return ""

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Divise le texte en chunks pour le traitement"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Essayer de couper à la fin d'une phrase
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                cut_point = max(last_period, last_newline)
                if cut_point > start + chunk_size // 2:
                    chunk = text[start:cut_point + 1]
                    end = cut_point + 1

            chunks.append(chunk.strip())
            start = end - overlap if end < len(text) else end

        return chunks

    def generate_faq_from_text(self, text: str) -> List[Dict[str, str]]:
        """Génère des questions/réponses à partir d'un texte via Ollama"""
        if not self.check_ollama_connection():
            raise Exception("Ollama n'est pas accessible")

        # Prompt pour générer des FAQ
        prompt = f"""
À partir du texte suivant, génère 3 à 5 questions-réponses pertinentes pour une FAQ.
Format de réponse : utilisez EXACTEMENT ce format JSON :
[
  {{"question": "Question 1?", "answer": "Réponse détaillée 1"}},
  {{"question": "Question 2?", "answer": "Réponse détaillée 2"}}
]

Texte source :
{text[:2000]}...

Générez uniquement le JSON, sans autre texte.
"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')

                # Tenter de parser le JSON généré
                try:
                    # Nettoyer le texte généré
                    cleaned_text = generated_text.strip()
                    if cleaned_text.startswith('```json'):
                        cleaned_text = cleaned_text[7:]
                    if cleaned_text.endswith('```'):
                        cleaned_text = cleaned_text[:-3]

                    faq_list = json.loads(cleaned_text)
                    return faq_list if isinstance(faq_list, list) else []

                except json.JSONDecodeError as e:
                    self.logger.error(f"Erreur de parsing JSON: {e}")
                    self.logger.error(f"Texte généré: {generated_text}")
                    return []
            else:
                self.logger.error(f"Erreur Ollama: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Erreur lors de la génération FAQ: {e}")
            return []

    def process_pdf_to_faq(self, pdf_path: str) -> List[Dict[str, str]]:
        """Pipeline complet : PDF -> Texte -> Chunks -> FAQ"""
        # Extraire le texte
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return []

        # Diviser en chunks
        chunks = self.chunk_text(text, chunk_size=1500)

        all_faqs = []
        for i, chunk in enumerate(chunks[:3]):  # Limiter à 3 chunks pour éviter trop de génération
            self.logger.info(f"Traitement du chunk {i+1}/{min(3, len(chunks))}")
            faqs = self.generate_faq_from_text(chunk)
            all_faqs.extend(faqs)

        return all_faqs

    def get_available_models(self) -> List[str]:
        """Récupère la liste des modèles disponibles dans Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des modèles: {e}")
            return []
