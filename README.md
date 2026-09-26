# VTUva 🎓

**VTUva** is an AI-powered study assistant and Previous Year Question (PYQ) processing system tailored for **Visvesvaraya Technological University (VTU)** engineering students. 

It combines a **Retrieval-Augmented Generation (RAG)** pipeline with a **multi-stage PYQ analysis engine** that parses PDF question papers, cleans watermark artifacts, clusters semantically similar questions across exam years, calculates repetition frequencies per module, and provides instant answers with source citations.

---

## 🌟 Key Features

* 📄 **Automated PDF PYQ Extraction:** Parses VTU PDF question papers using [Docling](https://github.com/DS4SD/docling) to extract structural grid tables, headers, sub-questions, marks, Bloom's Taxonomy levels (`L1`–`L6`), and Course Outcomes (`CO1`–`CO5`).
* 🧠 **Semantic Similarity Clustering:** Groups reworded/repeated questions across exam years using `sentence-transformers` (`all-MiniLM-L6-v2`) and cosine similarity.
* 📊 **Module-Wise Question Frequency:** Ranks questions by historical exam appearance frequency per module to highlight high-yield study topics.
* ⚡ **Streaming RAG Search:** Real-time answer generation via Server-Sent Events (SSE) using Google Gemini API (`gemini-2.5-flash-lite` / `gemini-1.5-flash`) or local Ollama models.
* 🏷️ **Universal Multi-Subject Support:** Dynamic subject code detection (e.g., `BCS501`, `BCHEC102`, `BCHES102`, `BMAT101`, `21CS51`) from filenames, PDF headers, or metadata folders.
* 📜 **Source Attributions:** Provides exact document page snippets and file references for every generated answer.

---

## 🏗️ System Architecture

```text
                                  VTUva System
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
    PYQ Analysis Engine                                    RAG Search Engine
            │                                                     │
   1. PDF Collection & Metadata                           1. User Query Stream
   2. Docling PDF Conversion                              2. Context Rewriting
   3. Regex Cleaning & Parsing                            3. Chroma Vector Retrieval (k=4)
   4. SentenceTransformers Clustering                     4. Gemini LLM Answer Generation
   5. Frequency & Repetition Indexing                             │
            │                                                     │
            └──────────────────────────┬──────────────────────────┘
                                       ▼
                             FastAPI + Web Dashboard
```

---

## 📦 Data & Pipeline Flow

| Step | Component | Tool / Technology | Purpose |
| :--- | :--- | :--- | :--- |
| **1** | PDF Collection | Python + File System | Organizes files (`data/pyq/<BRANCH>/<SUBJECT>/<YEAR>.pdf`) & extracts metadata |
| **2** | PDF Table Extraction | Docling (`docling-ibm-models`) | Converts PDF question papers to structured markdown tables |
| **3** | Question Parsing | Python + Regex | Extracts main questions, sub-questions (`a`, `b`, `c`), marks, & cleans watermarks |
| **4** | Repetition Analysis | `sentence-transformers` + Cosine | Clusters semantically similar questions across different exam years |
| **5** | Vector Storage | ChromaDB | Stores vector embeddings of notes, question papers, and frequency summaries |
| **6** | Web API | FastAPI + Uvicorn | Exposes endpoints for streaming chat, history, and document serving |
| **7** | User Interface | HTML5 / JS / Tailwind / SSE | Renders real-time streaming answers with source citations |

---

## 🚀 Getting Started

### Prerequisites

* **Python:** 3.10 or higher (Python 3.13 recommended)
* **API Key:** Google Gemini API Key (set in `.env` as `GEMINI_API_KEY`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rajeshgowda116/VTUva.git
   cd VTUva
   ```

2. **Set up Virtual Environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv env
   .\env\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv env
   source env/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install docling torchvision docling-ibm-models
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

---

## ⚙️ Usage

### 1. Ingest Documents & PYQ Papers

To process all course PDFs and past question papers in the `data/` directory and build the ChromaDB index:

```bash
python backend/rag/ingest.py
```

### 2. Run the Backend API & Server

Start the FastAPI server:

```bash
python backend/main.py
```

The server runs at: `http://localhost:8000`

### 3. Access the Web Dashboard

Open your browser and navigate to:
```text
http://localhost:8000
```

---

## 📊 Example Output: PYQ Repetition Analysis

When asking VTUva for repeated questions for a subject (e.g., `BCS501` - Software Engineering & Project Management), the system computes:

```json
{
  "subject_code": "BCS501",
  "module": 1,
  "canonical_question": "Explain the activities performed in a software process framework?",
  "frequency": 3,
  "papers": ["Dec 2024/Jan 2025", "June/July 2025", "Model Paper Set 1"],
  "instances": [
    {
      "question_number": "Q2 (a)",
      "marks": 6,
      "question_text": "Explain the activities performed in a software process framework?"
    },
    {
      "question_number": "Q1 (b)",
      "marks": 10,
      "question_text": "Explain the five activities that a generic process framework for software engineering encompasses"
    }
  ]
}
```

---

## 🛠️ Project Structure

```text
VTUva/
├── backend/
│   ├── main.py                  # FastAPI server & streaming API endpoints
│   ├── pyq_processor.py         # Multi-subject PDF PYQ extraction & parsing engine
│   ├── database.py              # SQLAlchemy DB setup (SQLite)
│   ├── models.py                # SQL database models (ChatHistory)
│   ├── schemas.py               # Pydantic request/response schemas
│   └── rag/
│       ├── pipeline.py          # RAG context retriever & execution pipeline
│       ├── retriever.py         # ChromaDB retriever singleton
│       ├── embeddings.py        # SentenceTransformer embedding loader
│       ├── generate.py          # Gemini API streaming & answer generation
│       ├── ingest.py            # Dynamic multi-subject PDF & PYQ ingestion
│       ├── loader.py            # PDF document reader
│       ├── splitter.py          # Text chunking module
│       └── vectordb.py          # ChromaDB vector store wrapper
├── frontend/
│   ├── index.html               # Main dashboard HTML interface
│   ├── app.js                  # Frontend SSE stream handler & UI logic
│   └── styles.css              # Custom styling
├── data/
│   ├── frist_sem/               # Textbook notes & syllabus PDFs
│   └── prev_qustions/           # Past year VTU PDF question papers
├── requirements.txt             # Python project dependencies
└── README.md                    # Project documentation
```

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
