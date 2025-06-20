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

if __name__ == "__main__":
    # Exemple de test : extraire le texte d'un PDF dans uploads/
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads/Entrepreneur-dActivites-Numeriques-Numeric-Factory-Brochure-MNS.pdf"))
    if not os.path.exists(pdf_path):
        print(f"Fichier introuvable : {pdf_path}")
    else:
        pages = extract_text_from_pdf(pdf_path)
        for i, text in enumerate(pages):
            print(f"--- Page {i+1} ---\n{text[:500]}\n")  # Affiche les 500 premiers caractères de chaque page
