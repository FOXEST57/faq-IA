import fitz  # PyMuPDF
from typing import List
import os

def extract_text_from_pdf(pdf_path: str) -> List[str]:
    """
    Extrait le texte de chaque page d'un PDF et retourne une liste de textes (un par page).
    """
    texts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            texts.append(page.get_text())
    return texts

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Découpe un texte en chunks de taille fixe avec un chevauchement.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks

if __name__ == "__main__":
    # Exemple de test : extraire le texte d'un PDF dans uploads/
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads/Entrepreneur-dActivites-Numeriques-Numeric-Factory-Brochure-MNS.pdf"))
    if not os.path.exists(pdf_path):
        print(f"Fichier introuvable : {pdf_path}")
    else:
        pages = extract_text_from_pdf(pdf_path)
        for i, text in enumerate(pages):
            print(f"--- Page {i+1} ---")
            chunks = chunk_text(text)
            for j, chunk in enumerate(chunks):
                print(f"Chunk {j+1} : {chunk[:100]}...")
            print()
