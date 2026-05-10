import torch
import cv2
import numpy as np
from PIL import Image
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from model_v2 import HTRModelV2, ctc_beam_search_decode
from dataset_lines import CHAR2IDX, IDX2CHAR, NUM_CLASSES, IMG_HEIGHT, IMG_WIDTH

CHECKPOINT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'checkpoints_v2', 'best_model_v2.pth'
)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# ── Load model once at module level ───────────────────────────────
def load_model():
    model = HTRModelV2(num_classes=NUM_CLASSES).to(DEVICE)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print(f"HTR Model loaded - Best CER: {checkpoint['val_cer']:.4f}")
    return model

_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model

# ── Preprocess image ──────────────────────────────────────────────
def preprocess_image(image_input):
    if isinstance(image_input, Image.Image):
        img = np.array(image_input.convert('L'))
    elif isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 3:
            img = cv2.cvtColor(image_input, cv2.COLOR_BGR2GRAY)
        else:
            img = image_input
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    else:
        raise ValueError(f"Unsupported input type: {type(image_input)}")

    h, w = img.shape
    new_w = min(IMG_WIDTH, int(w * IMG_HEIGHT / h))
    img = cv2.resize(img, (new_w, IMG_HEIGHT))
    padded = np.ones((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8) * 255
    padded[:, :new_w] = img
    img = padded.astype(np.float32) / 255.0
    img = (img - 0.5) / 0.5
    tensor = torch.tensor(img).unsqueeze(0).unsqueeze(0)
    return tensor.to(DEVICE)

# ── Predict single word/line ───────────────────────────────────────
def predict(image_input, use_beam=True):
    model = get_model()
    tensor = preprocess_image(image_input)
    with torch.no_grad():
        log_probs = model(tensor)
    if use_beam:
        results = ctc_beam_search_decode(
            log_probs.cpu(), IDX2CHAR, beam_width=10)
    else:
        from model import ctc_greedy_decode
        results = ctc_greedy_decode(log_probs.cpu(), IDX2CHAR)
    return results[0]

# ── Extract text from full page image ─────────────────────────────
def extract_text_from_page(page_image):
    if isinstance(page_image, Image.Image):
        img = np.array(page_image.convert('L'))
    else:
        img = page_image

    # Binarize
    _, binary = cv2.threshold(
        img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find text line regions using horizontal projection
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)
    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours top to bottom
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])

    lines = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h < 10 or w < 20:
            continue
        # Add padding
        pad = 5
        y1 = max(0, y - pad)
        y2 = min(img.shape[0], y + h + pad)
        x1 = max(0, x - pad)
        x2 = min(img.shape[1], x + w + pad)
        line_img = img[y1:y2, x1:x2]
        line_pil = Image.fromarray(line_img)
        text = predict(line_pil, use_beam=True)
        if text.strip():
            lines.append(text)

    return '\n'.join(lines) if lines else predict(
        Image.fromarray(img), use_beam=True)

# ── PDF page extraction (replaces Gemini Vision) ──────────────────
def extract_text_from_pdf_page(pil_image):
    return extract_text_from_page(pil_image)

if __name__ == '__main__':
    print("Testing inference...")
    test_img = Image.new('L', (200, 32), color=255)
    result = predict(test_img)
    print(f"Test prediction: '{result}'")
    print("Inference module ready.")