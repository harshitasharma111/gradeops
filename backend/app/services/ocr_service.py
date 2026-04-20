from google import genai
from google.genai import types
from pdf2image import convert_from_path
from PIL import Image
import os
import io
import time
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def pdf_to_images(pdf_path: str) -> list:
    pages = convert_from_path(pdf_path, dpi=300)
    return pages

def pil_to_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

def extract_text_from_page(image: Image.Image, retries: int = 4) -> str:
    prompt = """You are an expert at reading handwritten exam answers.
    
    Look at this exam page carefully and extract ALL handwritten and printed text exactly as written.
    
    Format your response as:
    - Preserve the structure of the answer
    - If you see a question number, include it
    - If handwriting is unclear, make your best guess and mark it with [unclear]
    - Extract every word, number, formula, and diagram description you can see
    
    Return only the extracted text, nothing else."""

    image_bytes = pil_to_bytes(image)

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt
                ]
            )
            return response.text.strip()

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = (2 ** attempt) * 5
                print(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{retries}")
                time.sleep(wait_time)
            else:
                raise e

    return "[Error: Rate limit exceeded after all retries]"

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
