# GradeOps 🎓

> **AI-powered Human-in-the-Loop exam grading platform** — Automates handwritten exam grading using a custom-trained CNN+BiLSTM+CTC Vision model, Agentic LLMs, and a full ML analytics pipeline, with Teaching Assistants as the final decision makers.

---

## 🧠 What is GradeOps?

Grading handwritten exams is time-consuming, inconsistent, and prone to fatigue-induced bias. GradeOps solves this by building a complete AI pipeline that:

1. **Reads** scanned handwritten PDFs using a **custom-trained HTR model** (CNN + BiLSTM + CTC) trained from scratch on the IAM Handwriting Dataset
2. **Grades** each answer against a structured rubric using a Langgraph agentic pipeline powered by Llama 3.3 70B
3. **Presents** AI-proposed grades to Teaching Assistants in a split-screen review dashboard with keyboard shortcuts
4. **Analyzes** class performance using a full DS/ML analytics stack
5. **Detects** plagiarism using sentence embeddings and cosine similarity

The system is designed so **AI proposes, humans decide** — ensuring fairness and accountability at scale.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  Login/Register → Instructor Dashboard → TA Review Dashboard     │
│  Analytics Dashboard (5 tabs) → Recharts Visualizations          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (CORS)
┌─────────────────────────▼───────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  JWT Auth → RBAC → Course/Exam/Rubric APIs → Grading APIs        │
│  Analytics APIs → Insights APIs → Prediction APIs               │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐ ┌────▼──────────┐
│  PostgreSQL  │ │  Custom    │ │  Groq +  │ │  scikit-learn │
│  SQLAlchemy  │ │  HTR Model │ │ Llama3.3 │ │  sentence-    │
│  Alembic     │ │CNN+BiLSTM  │ │ Langgraph│ │  transformers │
└─────────────┘ └────────────┘ └──────────┘ └───────────────┘
```

---

## 🤖 AI / ML Pipeline

### 1. Custom HTR Model — Trained from Scratch on IAM Dataset

Instead of using a third-party OCR API, we trained our own **Handwritten Text Recognition (HTR)** model from scratch.

**Architecture: CNN + BiLSTM + CTC**

```
Scanned Exam Page
        ↓
CNN with Residual Blocks (5 layers)
— ResidualBlock connections prevent vanishing gradients
— BatchNorm + ReLU activations
— Extracts visual features from handwriting strokes
        ↓
Bidirectional LSTM (2 layers, hidden=256)
— Reads feature sequence left→right AND right→left
— Temporal Attention weights important timesteps
        ↓
CTC (Connectionist Temporal Classification)
— Handles variable-length outputs without pre-segmentation
— Beam Search decoding (width=10) for accuracy
        ↓
Extracted Text
```

**Training Details:**
- Dataset: IAM Handwriting Word Database (115,320 word images, 657 writers)
- Split: 90% train / 5% validation / 5% test
- Optimizer: AdamW (lr=3e-4, weight_decay=1e-4)
- Scheduler: Cosine Annealing LR over 50 epochs
- Gradient Clipping: 5.0 (prevents exploding gradients in LSTM)
- Hardware: NVIDIA RTX 4060 Laptop GPU (8GB VRAM)
- Training Time: ~2 hours

**Data Augmentation:**
- Random rotation (±5°)
- Random brightness/contrast variation
- Elastic distortion (simulates natural handwriting variation)
- Random perspective transform

**Results:**

| Metric | Value |
|--------|-------|
| Best Validation CER | **10.37%** |
| Test CER | **12.18%** |
| Test WER | **31.94%** |
| Character Accuracy | **87.82%** |

### 2. Agentic Grading — Langgraph + Llama 3.3 70B (Groq)

A **4-node Langgraph state graph** processes each answer:

```
[evaluate_conditions] → [calculate_score] → [generate_justification] → [confidence_check]
```

- **evaluate_conditions:** Checks each rubric condition independently via LLM
- **calculate_score:** Aggregates partial credit scores
- **generate_justification:** Writes professional 2-3 sentence feedback
- **confidence_check:** Computes confidence score, flags urgent reviews

### 3. Plagiarism Detection — Sentence Embeddings + Cosine Similarity
- Embeds all student answers using `sentence-transformers` (`all-MiniLM-L6-v2`)
- Computes pairwise cosine similarity matrix
- Flags answer pairs above 0.85 similarity threshold
- Catches paraphrasing — semantic similarity, not keyword matching

### 4. Grade Prediction — Random Forest (scikit-learn)
- Extracts 8 engineered text features from OCR output
- Trains Random Forest classifier on historical graded answers
- Predicts score range: **high / medium / low** with probability scores

### 5. Answer Quality Clustering — K-Means (scikit-learn)
- Encodes student answers as sentence embeddings
- Clusters using K-Means with StandardScaler normalization
- Auto-labels clusters: High Quality / Partial Understanding / Needs Improvement

### 6. Statistical Analysis — Pandas + NumPy + SciPy
- **Pearson Correlation:** Word count vs score with p-value significance testing
- **Confidence Calibration:** AI confidence vs actual TA approval rate curve
- **Rubric Optimization:** Flags too-strict/too-easy rubric conditions

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | JWT (python-jose) + bcrypt |

### AI / ML
| Purpose | Technology |
|---------|-----------|
| Handwriting OCR | Custom CNN+BiLSTM+CTC (PyTorch) — trained from scratch |
| OCR Training Data | IAM Handwriting Dataset (Kaggle) |
| Agentic Grading | Langgraph + Langchain |
| LLM Inference | Groq API (Llama 3.3 70B) |
| Sentence Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| ML Models | scikit-learn (Random Forest, K-Means, cosine similarity) |
| Statistical Analysis | pandas, numpy, scipy |
| Model Persistence | PyTorch checkpoint + joblib |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React + TypeScript |
| Styling | Tailwind CSS |
| Routing | React Router |
| HTTP Client | Axios |
| Charts | Recharts |

---

## 🗄️ Database Schema

```
users
├── courses (instructor_id → users.id)
│   ├── course_assignments (ta_id → users.id)
│   └── exams (created_by → users.id)
│       ├── questions
│       │   └── rubric_conditions
│       ├── student_submissions
│       │   └── answer_extractions
│       │       └── ai_grades
│       │           └── final_grades (reviewed_by → users.id)
│       └── plagiarism_flags
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- NVIDIA GPU with CUDA (for HTR model training/inference)

### Backend Setup

```bash
git clone https://github.com/harshitasharma111/gradeops.git
cd gradeops/backend

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Fill in GROQ_API_KEY and DATABASE_URL

alembic upgrade head
uvicorn app.main:app --reload
```

### OCR Model Setup

```bash
cd gradeops
py -3.11 -m venv ocr_env
ocr_env\Scripts\activate

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install opencv-python numpy matplotlib pillow editdistance scipy

# Download IAM dataset from Kaggle
kaggle datasets download -d nibinv23/iam-handwriting-word-database
mkdir ocr_data
tar -xf iam-handwriting-word-database.zip -C ocr_data

# Train (~2 hours on RTX 4060)
python ocr_model/train.py

# Test inference
python ocr_model/inference.py
```

### Frontend Setup

```bash
cd gradeops/frontend
npm install
npm start
```

### Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/gradeops
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GROQ_API_KEY=your_groq_api_key
```

---

## 📱 Application Flow

### Instructor Workflow
1. Register → Create courses
2. Build exams with questions and rubric conditions
3. Upload student PDF scans
4. Trigger OCR (custom HTR model) → AI grading pipeline
5. View analytics dashboard (5 tabs)
6. Review plagiarism flags

### TA Workflow
1. Register as TA → Get assigned to courses
2. See pending review queue sorted by urgency
3. Split-screen: handwritten answer (left) + AI grade + justification (right)
4. **A** = Approve, **O** = Override, **← →** = Navigate

---

## 📊 Analytics Dashboard (5 Tabs)

| Tab | What it shows | Tech |
|-----|--------------|------|
| **Overview** | Score distribution, pass/fail, difficulty index | pandas, numpy, Recharts |
| **K-Means Clustering** | Answer quality groups | sentence-transformers, KMeans |
| **Correlation Analysis** | Word count vs score Pearson r | scipy.stats, ScatterChart |
| **Confidence Calibration** | AI confidence vs TA approval rate | numpy, LineChart |
| **Rubric Optimization** | Flags poorly designed conditions | Statistical analysis |

---

## 🧪 Key ML/DL Concepts Demonstrated

- **Custom HTR from Scratch** — CNN+BiLSTM+CTC on IAM dataset, CER 10.37%
- **Residual Connections** — Prevents vanishing gradients in deep CNN
- **Bidirectional LSTM** — Captures context from both sequence directions
- **CTC Loss** — Variable-length sequence alignment without pre-segmentation
- **Beam Search Decoding** — Outperforms greedy CTC decoding
- **Data Augmentation** — Elastic distortion, perspective transform, rotation
- **Agentic AI** — Multi-node Langgraph pipeline with shared state
- **Sentence Embeddings** — Semantic text representation (384 dimensions)
- **Unsupervised Learning** — K-Means clustering of answer quality
- **Supervised Learning** — Random Forest grade prediction
- **Statistical Testing** — Pearson r with p-value significance
- **Model Evaluation** — CER/WER metrics + confidence calibration curves
- **Human-in-the-Loop** — AI proposes, TA decides

---

## 👩‍💻 Project Structure

```
gradeops/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Database, auth, dependencies
│   │   ├── models/       # SQLAlchemy models
│   │   └── services/     # AI/ML business logic
│   ├── alembic/          # Database migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        # React pages
│       ├── services/     # API client
│       └── context/      # Auth context
├── ocr_model/
│   ├── dataset.py        # IAM dataset loader + augmentation pipeline
│   ├── model.py          # CNN+BiLSTM+CTC + Beam Search decoder
│   ├── train.py          # Training loop + CosineAnnealingLR + CER/WER
│   └── inference.py      # Inference + PDF page text extraction
└── storage/
    └── exams/            # Uploaded PDF files
```

---

## 📈 CV Highlights

**For Software Engineering CV:**
- Full-stack FastAPI + React + PostgreSQL application
- JWT auth with Role-Based Access Control (Instructor/TA)
- 20+ REST API endpoints with Pydantic validation
- Production patterns: migrations, CORS, dependency injection, retry logic

**For Data Science / ML CV:**
- Trained custom CNN+BiLSTM+CTC HTR model from scratch — CER 10.37%
- CTC loss with beam search decoding on IAM handwriting benchmark
- Data augmentation: elastic distortion, perspective transform
- NLP pipeline: OCR → embeddings → clustering → grading
- K-Means clustering, Random Forest, cosine similarity plagiarism detection
- Pearson correlation with statistical significance testing
- Confidence calibration analysis for ML model evaluation

---

## 🙏 Acknowledgements

- [IAM Handwriting Database](https://www.kaggle.com/datasets/nibinv23/iam-handwriting-word-database) — Training dataset
- [SimpleHTR](https://github.com/githubharald/SimpleHTR) — Reference architecture
- [Groq](https://groq.com) — Ultra-fast LLM inference
- [Langgraph](https://langchain-ai.github.io/langgraph/) — Agentic AI framework
- [Sentence Transformers](https://www.sbert.net) — Semantic embeddings