#!/usr/bin/env python3
"""
Script de test pour vérifier le fonctionnement d'Ollama
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.ollama_rag import OllamaRAGService
import requests

def test_ollama_connection():
    """Test de connexion à Ollama"""
    print("=== Test de connexion à Ollama ===")

    # Test direct de l'API
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        print(f"Réponse API Ollama: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Modèles disponibles: {[m['name'] for m in data.get('models', [])]}")
        else:
            print(f"Erreur API: {response.text}")
    except Exception as e:
        print(f"Erreur connexion directe: {e}")

    # Test via le service RAG
    try:
        rag_service = OllamaRAGService()
        status = rag_service.check_ollama_connection()
        print(f"Status via RAGService: {status}")

        if status:
            models = rag_service.get_available_models()
            print(f"Modèles via RAGService: {models}")

    except Exception as e:
        print(f"Erreur RAGService: {e}")

def test_text_generation():
    """Test de génération de texte"""
    print("\n=== Test de génération de texte ===")

    try:
        rag_service = OllamaRAGService()

        # Test avec un texte simple
        test_text = """
        Python est un langage de programmation interprété, multi-paradigme et multiplateformes. 
        Il favorise la programmation impérative structurée, fonctionnelle et orientée objet.
        """

        faqs = rag_service.generate_faq_from_text(test_text)
        print(f"Nombre de FAQ générées: {len(faqs) if faqs else 0}")

        if faqs:
            for i, faq in enumerate(faqs, 1):
                print(f"FAQ {i}:")
                print(f"  Question: {faq.get('question', 'N/A')}")
                print(f"  Réponse: {faq.get('answer', 'N/A')[:100]}...")
        else:
            print("Aucune FAQ générée")

    except Exception as e:
        print(f"Erreur génération: {e}")

if __name__ == "__main__":
    test_ollama_connection()
    test_text_generation()
