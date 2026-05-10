from pdf2image import convert_from_path
from PIL import Image
import os
import sys

OCR_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
    'ocr_model'
)
sys.path.append(OCR_MODEL_PATH)

try:
    from inference import extract_text_from_pdf_page
    HTR_AVAILABLE = True
    print("✅ Custom HTR V2 model loaded successfully")
except Exception as e:
    HTR_AVAILABLE = False
    print(f"⚠️ HTR model not available: {e}")

def pdf_to_images(pdf_path: str) -> list:
    return convert_from_path(pdf_path, dpi=300)

def extract_text_from_pdf(pdf_path: str) -> dict:
    try:
        pages = pdf_to_images(pdf_path)
    except Exception as e:
        return {"error": f"Failed to convert PDF: {str(e)}"}

    extracted = {}
    for i, page in enumerate(pages):
        try:
            if HTR_AVAILABLE:
                text = extract_text_from_pdf_page(page)
                extracted[f"page_{i+1}"] = text.strip() or "[No text detected]"
            else:
                extracted[f"page_{i+1}"] = "[HTR model not available]"
        except Exception as e:
            extracted[f"page_{i+1}"] = f"[Error: {str(e)}]"

    return extracted