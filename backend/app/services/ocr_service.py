from pdf2image import convert_from_path
from PIL import Image
import os
import sys
import time

# Add ocr_model to path
OCR_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
    'ocr_model'
)
sys.path.append(OCR_MODEL_PATH)

# Load our trained HTR model
try:
    from inference import extract_text_from_pdf_page, predict
    HTR_AVAILABLE = True
    print("✅ Custom HTR model loaded successfully")
except Exception as e:
    HTR_AVAILABLE = False
    print(f"⚠️ HTR model not available: {e}. Falling back to basic OCR.")

def pdf_to_images(pdf_path: str) -> list:
    pages = convert_from_path(pdf_path, dpi=300)
    return pages

def extract_text_from_page(image: Image.Image) -> str:
    if HTR_AVAILABLE:
        try:
            text = extract_text_from_pdf_page(image)
            return text.strip() if text.strip() else "[No text detected]"
        except Exception as e:
            return f"[HTR Error: {str(e)}]"
    else:
        return "[HTR model not available]"

def extract_text_from_pdf(pdf_path: str) -> dict:
    try:
        pages = pdf_to_images(pdf_path)
    except Exception as e:
        return {"error": f"Failed to convert PDF: {str(e)}"}

    extracted = {}
    for i, page in enumerate(pages):
        try:
            text = extract_text_from_page(page)
            extracted[f"page_{i+1}"] = text
        except Exception as e:
            extracted[f"page_{i+1}"] = f"Error extracting page: {str(e)}"

    return extracted