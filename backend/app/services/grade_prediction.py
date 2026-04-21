import numpy as np
import joblib
import os
import re
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from sqlalchemy.orm import Session
from app.models.exam import AnswerExtraction, AIGrade

MODEL_PATH = "/Users/harshitasharma/GradeOps CC/gradeops/storage/grade_predictor.joblib"
ENCODER_PATH = "/Users/harshitasharma/GradeOps CC/gradeops/storage/label_encoder.joblib"

# ── Feature Extraction ─────────────────────────────────────────────────────────
def extract_features(text: str, max_marks: int) -> list:
    if not text or text in ["No text extracted", "[Error: Rate limit exceeded after all retries]"]:
        return [0, 0, 0, 0, 0, 0, 0, 0]

    word_count = len(text.split())
    char_count = len(text)
    sentence_count = len(re.findall(r'[.!?]+', text)) + 1
    has_formula = 1 if re.search(r'[A-Za-z]\s*=\s*[A-Za-z0-9]', text) else 0
    has_numbers = 1 if re.search(r'\d+', text) else 0
    avg_word_length = np.mean([len(w) for w in text.split()]) if text.split() else 0
    has_definition = 1 if any(word in text.lower() for word in ['is', 'are', 'defined', 'means', 'refers']) else 0
    normalized_length = min(word_count / 100, 1.0)

    return [
        word_count,
        char_count,
        sentence_count,
        has_formula,
        has_numbers,
        avg_word_length,
        has_definition,
        normalized_length
    ]

def score_to_label(score: float, max_marks: int) -> str:
    percentage = (score / max_marks) * 100 if max_marks > 0 else 0
    if percentage >= 70:
        return "high"
    elif percentage >= 40:
        return "medium"
    else:
        return "low"

# ── Train Model ────────────────────────────────────────────────────────────────
def train_model(db: Session) -> dict:
    extractions = db.query(AnswerExtraction).all()

    X = []
    y = []

    for extraction in extractions:
        if not extraction.ai_grade:
            continue

        ai_grade = extraction.ai_grade
        final_grade = ai_grade.final_grade

        score = final_grade.final_score if final_grade and final_grade.final_score is not None else ai_grade.total_score
        max_marks = ai_grade.max_marks

        if score is None or max_marks is None or max_marks == 0:
            continue

        features = extract_features(extraction.extracted_text, max_marks)
        label = score_to_label(score, max_marks)

        X.append(features)
        y.append(label)

    if len(X) < 5:
        return {"error": f"Not enough data to train. Need at least 5 graded answers, have {len(X)}."}

    X = np.array(X)
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    if len(set(y)) < 2:
        return {"error": "Need at least 2 different score categories to train."}

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)

    feature_names = ["word_count", "char_count", "sentence_count", "has_formula",
                     "has_numbers", "avg_word_length", "has_definition", "normalized_length"]
    importances = dict(zip(feature_names, model.feature_importances_.tolist()))

    return {
        "status": "Model trained successfully",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(report["accuracy"], 3),
        "feature_importances": importances,
        "class_distribution": {label: y.count(label) for label in set(y)}
    }

# ── Predict ────────────────────────────────────────────────────────────────────
def predict_score(text: str, max_marks: int) -> dict:
    if not os.path.exists(MODEL_PATH):
        return {"error": "Model not trained yet. Train the model first."}

    model = joblib.load(MODEL_PATH)
    le = joblib.load(ENCODER_PATH)

    features = np.array([extract_features(text, max_marks)])
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]

    label = le.inverse_transform([prediction])[0]
    prob_dict = {le.classes_[i]: round(float(probabilities[i]), 3) for i in range(len(le.classes_))}

    return {
        "predicted_range": label,
        "probabilities": prob_dict,
        "confidence": round(float(max(probabilities)), 3)
    }
