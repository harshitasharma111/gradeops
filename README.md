# GradeOps 🎓

> **AI-powered Human-in-the-Loop exam grading platform** — Automates handwritten exam grading using custom-trained HTR models (CNN+BiLSTM+CTC), Agentic LLMs, and a full ML analytics pipeline, with Teaching Assistants as the final decision makers.

---

## What is GradeOps?

Grading handwritten exams is time-consuming, inconsistent, and prone to fatigue-induced bias. GradeOps solves this by building a complete AI pipeline that:

1. **Reads** scanned handwritten PDFs using a **custom-trained HTR model** trained from scratch on the IAM Handwriting Dataset
2. **Grades** each answer against a structured rubric using a Langgraph agentic pipeline powered by Llama 3.3 70B
3. **Presents** AI-proposed grades to Teaching Assistants in a split-screen review dashboard with keyboard shortcuts
4. **Analyzes** class performance using a full DS/ML analytics stack
5. **Detects** plagiarism using sentence embeddings and cosine similarity

The system is designed so **AI proposes, humans decide** — ensuring fairness and accountability at scale.

---

## System Architecture

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

## AI / ML Pipeline

### 1. Custom HTR Models — Trained from Scratch

We trained two versions of our Handwritten Text Recognition (HTR) model from scratch on the IAM Handwriting Dataset.

#### V1 — Word-Level CNN+BiLSTM+CTC

```
Word Image (32×128px)
        ↓
CNN with Residual Blocks (5 layers, 32→512 channels)
— ResidualBlock skip connections prevent vanishing gradients
— BatchNorm + ReLU activations
        ↓
Bidirectional LSTM (2 layers, hidden=256)
— Reads sequence left→right AND right→left
— Temporal Attention weights important timesteps
        ↓
CTC Loss + Beam Search Decoding (width=5)
```

| Metric | Value |
|--------|-------|
| Best Val CER | 10.37% |
| Test CER | 12.18% |
| Test WER | 31.94% |
| Training Data | Word-level IAM (~35k samples) |
| Image Size | 32×128 px |

#### V2 — Line-Level CNN+BiLSTM+MultiHeadAttention+CTC

```
Line Image (64×512px)
        ↓
Deeper CNN with Residual Blocks (6 layers, GELU activations)
— Higher resolution captures finer handwriting details
        ↓
Bidirectional LSTM (3 layers, hidden=512)
— Larger capacity for line-level context
        ↓
Multi-Head Self Attention (8 heads)
— Direct connections between any two sequence positions
— Layer Normalization after attention
        ↓
CTC Loss + Beam Search Decoding (width=10)
```

| Metric | Value |
|--------|-------|
| Best Val CER | **4.11%** |
| Test CER | **5.35%** |
| Test WER | **21.24%** |
| Training Data | Line-level IAM (4,677 samples) |
| Image Size | 64×512 px |

**V1 → V2: 60% reduction in CER through line-level training and architectural improvements.**

**Training Configuration:**
- Dataset: IAM Handwriting Database (115,320 word images, 657 writers)
- Optimizer: AdamW (lr=3e-4, weight_decay=1e-4)
- V1 Scheduler: Cosine Annealing (50 epochs)
- V2 Scheduler: Cosine Annealing with Warm Restarts + 5-epoch LR warmup (100 epochs)
- Gradient Clipping: 5.0
- Hardware: NVIDIA RTX 4060 Laptop GPU (8GB VRAM)

**Data Augmentation:**
- Elastic distortion — simulates natural handwriting variability
- Random rotation (±5°)
- Random brightness/contrast variation
- Random perspective transform
- Random noise injection (V2)

---

### 2. Agentic Grading — Langgraph + Llama 3.3 70B

A **4-node Langgraph state graph** processes each answer:

```
[evaluate_conditions] → [calculate_score] → [generate_justification] → [confidence_check]
```

- **evaluate_conditions:** Evaluates each rubric condition independently via LLM — one focused prompt per condition for accuracy
- **calculate_score:** Aggregates partial credit scores, caps at max marks
- **generate_justification:** Writes professional 2-3 sentence feedback based on condition breakdown
- **confidence_check:** Computes confidence score, flags low-confidence papers for urgent TA review

### 3. Plagiarism Detection — Sentence Embeddings + Cosine Similarity

- Encodes all student answers using `sentence-transformers` (`all-MiniLM-L6-v2`) into 384-dimensional vectors
- Computes pairwise cosine similarity matrix across all submissions for a question
- Flags pairs above 0.85 similarity threshold — catches paraphrasing, not just copy-paste

### 4. Grade Prediction — Random Forest

- Extracts 8 engineered text features from OCR output (word count, sentence count, formula presence, etc.)
- Trains a Random Forest classifier on historical graded answers
- Predicts score range (high / medium / low) with probability scores on new answers

### 5. Answer Quality Clustering — K-Means

- Encodes student answers as sentence embeddings
- Clusters using K-Means (n=2 or 3) with StandardScaler normalization
- Automatically labels clusters as High Quality / Partial Understanding / Needs Improvement based on average score

### 6. Statistical Analytics — Pandas + NumPy + SciPy

- **Pearson Correlation:** Word count vs score per question with p-value significance testing
- **Confidence Calibration:** Compares AI stated confidence against actual TA approval rate across bins
- **Rubric Optimization:** Analyzes condition satisfaction rates, flags conditions that are too strict or too lenient
- **Grade Distribution:** Class average, median, std deviation, difficulty index, override rate

---

## Tech Stack

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
| Handwriting OCR V1 | Custom CNN+BiLSTM+CTC (PyTorch) — Word-level |
| Handwriting OCR V2 | Custom CNN+BiLSTM+MultiHeadAttention+CTC (PyTorch) — Line-level |
| OCR Training Data | IAM Handwriting Database (Kaggle) |
| Agentic Grading | Langgraph + Langchain |
| LLM Inference | Groq API (Llama 3.3 70B) |
| Sentence Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| ML Models | scikit-learn (Random Forest, K-Means, cosine similarity) |
| Statistical Analysis | pandas, numpy, scipy |
| Model Persistence | PyTorch checkpoint (.pth) + joblib |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React + TypeScript |
| Styling | Tailwind CSS |
| Routing | React Router |
| HTTP Client | Axios |
| Charts | Recharts |

---

## Database Schema

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

## Getting Started

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

### OCR Model Setup (Windows + CUDA)

```bash
cd gradeops
py -3.11 -m venv ocr_env
ocr_env\Scripts\activate

# Install PyTorch with CUDA 12.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install opencv-python numpy matplotlib pillow editdistance scipy

# Download datasets
kaggle datasets download -d nibinv23/iam-handwriting-word-database
kaggle datasets download -d adarsh203/iam-handwriting-lines

mkdir ocr_data
tar -xf iam-handwriting-word-database.zip -C ocr_data
mkdir ocr_data\iam_lines
tar -xf iam-handwriting-lines.zip -C ocr_data\iam_lines
tar -xf ocr_data\iam_lines\IAM_lines.tgz -C ocr_data\iam_lines

# Prepare line-level labels from word annotations
python ocr_model\prepare_lines.py

# Train V1 — word-level (~2 hours on RTX 4060)
python ocr_model\train.py

# Train V2 — line-level, best model (~4 hours on RTX 4060)
python ocr_model\train_v2.py

# Test inference
python ocr_model\inference.py
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

## Application Flow

### Instructor Workflow
1. Register → Create courses
2. Build exams with questions and granular rubric conditions dynamically
3. Upload student PDF scans
4. Trigger OCR (V2 HTR model) → AI grading pipeline
5. View analytics dashboard across 5 analysis tabs
6. Review plagiarism flags

### TA Workflow
1. Register as TA → Get assigned to courses by instructor
2. Review queue sorted by urgency (confidence score)
3. Split-screen: handwritten answer (left) + AI grade + justification (right)
4. **A** = Approve · **O** = Override · **← →** = Navigate

---

## Analytics Dashboard

| Tab | Analysis | Libraries |
|-----|----------|-----------|
| Overview | Score distribution, pass/fail rate, difficulty index per question | pandas, numpy, Recharts |
| K-Means Clustering | Answer quality groups using sentence embeddings | sentence-transformers, scikit-learn |
| Correlation Analysis | Pearson r between answer length and score, scatter plot | scipy.stats, Recharts |
| Confidence Calibration | AI confidence vs TA approval rate across confidence bins | numpy, Recharts |
| Rubric Optimization | Condition satisfaction rates, flags imbalanced conditions | Statistical analysis |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user (instructor/ta) |
| POST | `/auth/login` | Login, returns JWT |
| POST | `/courses/create` | Create a course |
| GET | `/courses/my-courses` | List courses for current user |
| POST | `/courses/{id}/assign-ta` | Assign TA to course |
| POST | `/exams/create` | Create exam with questions and rubric |
| POST | `/exams/{id}/upload-submission` | Upload student PDF |
| POST | `/exams/submissions/{id}/process` | Run HTR OCR |
| POST | `/grade/submission/{id}` | Grade all answers via Langgraph |
| GET | `/grade/pending-reviews` | Get pending TA review queue |
| POST | `/grade/review/{id}` | Approve or override a grade |
| GET | `/analytics/exam/{id}` | Full exam analytics |
| POST | `/analytics/exam/{id}/plagiarism` | Run plagiarism detection |
| GET | `/analytics/exam/{id}/export` | Export grades to Excel |
| GET | `/insights/exam/{id}/clusters` | K-Means answer clustering |
| GET | `/insights/exam/{id}/correlations` | Pearson correlation analysis |
| GET | `/insights/exam/{id}/calibration` | Confidence calibration |
| GET | `/insights/exam/{id}/rubric-optimization` | Rubric improvement suggestions |
| POST | `/predict/train` | Train grade prediction model |
| POST | `/predict/score` | Predict score range for an answer |

---

## Project Structure

```
gradeops/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/             # Database, auth, dependencies
│   │   ├── models/           # SQLAlchemy ORM models
│   │   └── services/         # AI/ML business logic
│   ├── alembic/              # Database migration files
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/            # React page components
│       ├── services/         # Axios API client
│       └── context/          # Auth context
├── ocr_model/
│   ├── dataset.py            # V1 word-level IAM dataset loader
│   ├── model.py              # V1 CNN+BiLSTM+CTC architecture
│   ├── train.py              # V1 training loop
│   ├── dataset_lines.py      # V2 line-level dataset loader
│   ├── model_v2.py           # V2 CNN+BiLSTM+MultiHeadAttention+CTC
│   ├── train_v2.py           # V2 training with warm restarts
│   ├── prepare_lines.py      # Builds line labels from word annotations
│   └── inference.py          # Inference pipeline + page segmentation
└── storage/
    └── exams/                # Uploaded student PDF files
```

---

## Authors

- Harshita Sharma
- Abhinav Chouhan