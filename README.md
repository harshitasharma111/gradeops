# GradeOps 🎓

> **AI-powered Human-in-the-Loop exam grading platform** — Automates handwritten exam grading using Vision-Language Models, Agentic LLMs, and a full ML analytics pipeline, with Teaching Assistants as the final decision makers.

---

## 🧠 What is GradeOps?

Grading handwritten exams is time-consuming, inconsistent, and prone to fatigue-induced bias. GradeOps solves this by building a complete AI pipeline that:

1. **Reads** scanned handwritten PDFs using Gemini Vision OCR
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
│  PostgreSQL  │ │   Gemini   │ │  Groq +  │ │  scikit-learn │
│  SQLAlchemy  │ │  Vision    │ │ Llama3.3 │ │  sentence-    │
│  Alembic     │ │  OCR       │ │ Langgraph│ │  transformers │
└─────────────┘ └────────────┘ └──────────┘ └───────────────┘
```

---

## 🤖 AI / ML Pipeline

### 1. OCR Layer — Gemini Vision

- Converts each PDF page to a high-resolution image using `pdf2image` + `poppler`
- Sends images to Gemini Vision API with a structured extraction prompt
- Extracts handwritten text per question with context preservation
- **Production feature:** Exponential backoff retry logic (5s → 10s → 20s → 40s) on rate limits

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
- Computes pairwise cosine similarity matrix using `scikit-learn`
- Flags answer pairs above 0.85 similarity threshold
- Stores flagged pairs with similarity scores in PostgreSQL

### 4. Grade Prediction — Random Forest (scikit-learn)

- Extracts 8 text features: word count, char count, sentence count, formula presence, number presence, avg word length, definition keywords, normalized length
- Trains a Random Forest classifier on historical graded answers
- Predicts score range: **high / medium / low** with probability scores
- Persists trained model using `joblib`

### 5. Answer Quality Clustering — K-Means (scikit-learn)

- Encodes student answers as sentence embeddings
- Clusters using K-Means with StandardScaler normalization
- Auto-labels clusters: High Quality / Partial Understanding / Needs Improvement
- Visualized in the analytics dashboard

### 6. Statistical Analysis — Pandas + NumPy + SciPy

- **Pearson Correlation:** Word count vs score correlation with p-value significance testing
- **Confidence Calibration:** Compares AI confidence vs actual TA approval rate across bins
- **Rubric Optimization:** Analyzes condition satisfaction rates, flags too-strict/too-easy conditions
- **Grade Analytics:** Class average, median, std deviation, difficulty index, override rate

---

## 🛠️ Tech Stack

### Backend

| Layer          | Technology                 |
| -------------- | -------------------------- |
| Web Framework  | FastAPI                    |
| Database       | PostgreSQL                 |
| ORM            | SQLAlchemy                 |
| Migrations     | Alembic                    |
| Authentication | JWT (python-jose) + bcrypt |
| Task Queuing   | FastAPI Background Tasks   |

### AI / ML

| Purpose              | Technology                                               |
| -------------------- | -------------------------------------------------------- |
| Handwriting OCR      | Gemini Vision API (google-genai)                         |
| Agentic Grading      | Langgraph + Langchain                                    |
| LLM Inference        | Groq API (Llama 3.3 70B)                                 |
| Sentence Embeddings  | sentence-transformers (all-MiniLM-L6-v2)                 |
| ML Models            | scikit-learn (Random Forest, K-Means, cosine similarity) |
| Statistical Analysis | pandas, numpy, scipy                                     |
| Model Persistence    | joblib                                                   |

### Frontend

| Layer       | Technology         |
| ----------- | ------------------ |
| Framework   | React + TypeScript |
| Styling     | Tailwind CSS       |
| Routing     | React Router       |
| HTTP Client | Axios              |
| Charts      | Recharts           |
| Icons       | Lucide React       |

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

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Homebrew (Mac) for poppler and tesseract

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/harshitasharma111/gradeops.git
cd gradeops/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Mac)
brew install poppler tesseract

# Set up environment variables
cp .env.example .env
# Fill in your API keys and database URL

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
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
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

---

## 📱 Application Flow

### Instructor Workflow

1. Register as Instructor → Create courses
2. Build exams with questions and granular rubric conditions
3. Upload student PDF scans (bulk supported)
4. Trigger OCR → AI grading pipeline
5. View analytics dashboard with 5 analysis tabs
6. Review plagiarism flags

### TA Workflow

1. Register as TA → Get assigned to courses by instructor
2. See pending review queue sorted by urgency
3. Split-screen review: handwritten answer (left) vs AI grade + justification (right)
4. Keyboard shortcuts: **A** = Approve, **O** = Override, **← →** = Navigate
5. Override with custom score and comment if needed

---

## 📊 Analytics Dashboard

The analytics dashboard has **5 tabs** powered by different ML/DS techniques:

| Tab                        | What it shows                                                          | Tech                                       |
| -------------------------- | ---------------------------------------------------------------------- | ------------------------------------------ |
| **Overview**               | Score distribution, pass/fail, difficulty index, per-question averages | pandas, numpy, Recharts                    |
| **K-Means Clustering**     | Student answers grouped by semantic similarity                         | sentence-transformers, scikit-learn KMeans |
| **Correlation Analysis**   | Word count vs score Pearson correlation with scatter plot              | scipy.stats, Recharts ScatterChart         |
| **Confidence Calibration** | AI confidence vs actual TA approval rate curve                         | numpy, Recharts LineChart                  |
| **Rubric Optimization**    | Flags too-strict or too-easy rubric conditions                         | Statistical analysis                       |

---

## 🔌 API Reference

### Auth

| Method | Endpoint         | Description                       |
| ------ | ---------------- | --------------------------------- |
| POST   | `/auth/register` | Register new user (instructor/ta) |
| POST   | `/auth/login`    | Login and get JWT token           |

### Courses

| Method | Endpoint                  | Description                      |
| ------ | ------------------------- | -------------------------------- |
| POST   | `/courses/create`         | Create a new course              |
| GET    | `/courses/my-courses`     | Get all courses for current user |
| POST   | `/courses/{id}/assign-ta` | Assign TA to course              |

### Exams

| Method | Endpoint                          | Description                           |
| ------ | --------------------------------- | ------------------------------------- |
| POST   | `/exams/create`                   | Create exam with questions and rubric |
| GET    | `/exams/course/{id}`              | Get all exams for a course            |
| POST   | `/exams/{id}/upload-submission`   | Upload student PDF                    |
| POST   | `/exams/submissions/{id}/process` | Run OCR on submission                 |

### Grading

| Method | Endpoint                 | Description                       |
| ------ | ------------------------ | --------------------------------- |
| POST   | `/grade/submission/{id}` | Grade all answers in a submission |
| GET    | `/grade/pending-reviews` | Get all pending TA reviews        |
| POST   | `/grade/review/{id}`     | Approve or override a grade       |

### Analytics & Insights

| Method | Endpoint                                  | Description                    |
| ------ | ----------------------------------------- | ------------------------------ |
| GET    | `/analytics/exam/{id}`                    | Full exam analytics            |
| POST   | `/analytics/exam/{id}/plagiarism`         | Run plagiarism check           |
| GET    | `/analytics/exam/{id}/export`             | Export grades to Excel         |
| GET    | `/insights/exam/{id}/clusters`            | K-Means clustering             |
| GET    | `/insights/exam/{id}/correlations`        | Pearson correlation analysis   |
| GET    | `/insights/exam/{id}/calibration`         | Confidence calibration         |
| GET    | `/insights/exam/{id}/rubric-optimization` | Rubric suggestions             |
| POST   | `/predict/train`                          | Train grade prediction model   |
| POST   | `/predict/score`                          | Predict score range for answer |

---

## 🧪 Key ML Concepts Demonstrated

- **Agentic AI** — Multi-node Langgraph pipeline with state management
- **Vision-Language Models** — Gemini Vision for handwriting OCR
- **Retrieval & Embedding** — Sentence embeddings for semantic similarity
- **Unsupervised Learning** — K-Means clustering of answer quality
- **Supervised Learning** — Random Forest grade prediction
- **Statistical Testing** — Pearson correlation with p-value significance
- **Model Evaluation** — Confidence calibration curves
- **Human-in-the-Loop** — AI proposes, TA decides architecture
- **Production Patterns** — Exponential backoff, JWT auth, RBAC, migrations

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
│       ├── components/   # Reusable components
│       ├── services/     # API client
│       └── context/      # Auth context
└── storage/
    └── exams/            # Uploaded PDF files
```

---

## 📈 CV Highlights

**For Software Engineering CV:**

- Full-stack application with FastAPI + React + PostgreSQL
- JWT authentication with Role-Based Access Control
- RESTful API design with 20+ endpoints
- Database migrations with Alembic
- Production patterns: retry logic, CORS, dependency injection

**For Data Science / ML CV:**

- End-to-end NLP pipeline: OCR → text extraction → embedding → grading
- Unsupervised ML: K-Means clustering with sentence embeddings
- Supervised ML: Random Forest with 8 engineered features
- Statistical analysis: Pearson correlation, p-value testing
- Model evaluation: Confidence calibration curves
- Agentic AI: Multi-node Langgraph grading pipeline
- Data visualization: 10+ Recharts chart types

---

## 🙏 Acknowledgements

- [Groq](https://groq.com) — Ultra-fast LLM inference
- [Google Gemini](https://ai.google.dev) — Vision-Language Model for OCR
- [Langgraph](https://langchain-ai.github.io/langgraph/) — Agentic AI framework
- [Sentence Transformers](https://www.sbert.net) — Semantic embeddings
