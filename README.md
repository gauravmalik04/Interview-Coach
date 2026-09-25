# GAIUS — Adaptive AI Technical Interview Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-AsyncIO-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG_Vector_Store-FF4B4B?style=flat)](https://www.trychroma.com/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Inference_API-FFD21E?style=flat&logo=huggingface&logoColor=black)](https://huggingface.co/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Presentation](https://img.shields.io/badge/Presentation-Google_Slides-EA4335?style=flat&logo=google-slides&logoColor=white)](https://docs.google.com/presentation/d/1oUL1YGlsIsbox-qexv6Wi-gmS7iTpwGW/edit?usp=sharing&ouid=111265406321287427023&rtpof=true&sd=true)

**GAIUS** is an enterprise-grade, full-stack adaptive technical interview platform engineered to simulate rigorous FAANG+ engineering interviews. Powered by asynchronous LLM multi-agents, vector-grounded RAG (ChromaDB), real-time WebSockets, and a 7-dimensional evaluation engine, GAIUS assesses candidates on both technical depth and communication invariants, paired with a dedicated AI Technical Mentor (**Hermes**).

> 📽️ **Project Presentation Deck**: [View Google Slides Presentation](https://docs.google.com/presentation/d/1oUL1YGlsIsbox-qexv6Wi-gmS7iTpwGW/edit?usp=sharing&ouid=111265406321287427023&rtpof=true&sd=true)
> 📽️ **Project Video Resource**: https://drive.google.com/drive/folders/1zuxIdiOqAYo6AqhQThFyGhxgtxeklQGn?usp=sharing
---

## 🌟 Key Features

### 1. Dual-Mode Technical Interviews
* **🎓 Coached Interview Mode**:
  * Designed for deliberate learning and guided practice.
  * Provides real-time expectation hints, optimal Big-O targets, and answer talking-points.
  * Resumable sessions: candidates can pause and resume active coached sessions anytime from the dashboard.
* **⚡ Real Interview Mode**:
  * Strict FAANG-style simulation.
  * Zero hints or in-session assistance; questions probe candidate reasoning progressively.
  * Anti-cheat & integrity safeguards: leaving, closing the tab, or disconnecting immediately finalizes the session without resumption.

### 2. Multi-Language Candidate Workbench
* Supported Languages: **Python 3**, **JavaScript (Node.js)**, **Java (OpenJDK)**, **C++ (GCC/Clang)**, and **Go (Golang)**.
* **Language Selection**: Radio button cards with generous spacing (max 3 per row) ensuring unambiguous selection and instant visual feedback.
* **Dynamic Starter Code**: Pre-populates clean question boilerplate customized to the selected language.
* **Collapsible Code Scratchpad**: Collapsed by default to maximize conversation area; expandable with a single click. Features starter code reset, copy to clipboard, and instant insert-into-chat.
* **Spacious Conversational View**: Wide chat interface supporting Markdown tables, formatted code blocks, and phase dividers.

### 3. Progressive 6-Phase Interview Flow
Every interview session transitions dynamically across structured engineering phases:
1. **Introduction**: Greeting, domain scope, and environment verification.
2. **Problem Presentation**: Formulates the problem statement, constraints, and initial examples.
3. **Approach & Invariants**: Probes candidate's algorithmic logic, mathematical invariants, and trade-offs before writing code.
4. **Implementation & Dry Run**: Candidate submits solution via chat or scratchpad; agent probes input validation and edge cases.
5. **Complexity Analysis**: Explicit derivation of worst-case and average-case time ($O$) and space ($O$) bounds.
6. **Conclusion**: Session wraps up cleanly with responses saved.

### 4. Dual-Thread Windowed State Memory Architecture
To optimize response latency while maintaining deep situational awareness, GAIUS employs a concurrent **Windowed State Architecture**:
* **Thread 1 — Fast Foreground Inference**: Slices the sliding conversational context window down to strictly the **last 2 turns**, minimizing token overhead and drastically lowering Time-To-First-Token (TTFT).
* **Thread 2 — Concurrent Background Extraction Worker**: Using `asyncio.create_task()`, an isolated background worker (`state_extractor.py`) evaluates candidate messages in parallel, extracting structured algorithmic facts without delaying the chat response.
* **Structured Situational State (`memory_state_json`)**: Persists cumulative observations in SQLite:
  * `data_structures_used`: Data structures identified or implemented (e.g., Hash Map, Monotonic Stack, Two Pointers).
  * `claimed_time_complexity` & `claimed_space_complexity`: Big-O bounds explicitly stated by the candidate.
  * `identified_edge_cases`: Edge boundaries discussed (empty arrays, duplicates, negative numbers).
  * `open_weaknesses`: Suboptimal choices, brute-force penalties, or unaddressed bottlenecks.
  * `key_algorithmic_approach`: Core algorithmic paradigm currently deployed.
* **Situational Awareness Injection**: The cumulative state is injected into the interviewer's system prompt and heuristic probing engine, ensuring targeted follow-up challenges tailored to open candidate weaknesses.

### 5. 7-Dimensional Evaluation Engine
Evaluates candidate performance across 7 core software engineering rubrics:
* **Algorithmic Logic & Invariants**: Correctness, optimal algorithmic paradigm selection.
* **Time & Space Complexity**: Big-O derivation, memory footprint, auxiliary space.
* **Data Structures Mastery**: Appropriate data structure choice and trade-off justification.
* **Edge Cases & Boundary Traps**: Handling empty inputs, off-by-one errors, overflow, duplicate keys.
* **Code Quality & Modularity**: Clean architecture, naming conventions, separation of concerns.
* **Problem Solving Rigor**: Systematic problem decomposition and structured reasoning.
* **Technical Communication**: Articulation of assumptions, active listening, structured explanation.

> **On-Demand Report Generation**: Evaluation reports are generated strictly on-demand. Concluding an interview is instantaneous without application freezing. Candidates can click **"Generate Evaluation Report ⚡"** or return directly to the dashboard.

### 6. Hermes — Vector-Grounded AI Technical Mentor
Dedicated pedagogical AI mentor equipped with multi-tool intent classification:
* **Candidate Weakness Analysis**: Inspects historical reports to identify recurring low-scoring dimensions.
* **Strengths & Highlights**: Surfaces top-scoring dimensions and evidence from recent interviews.
* **Scorecard Deep Dive**: Provides granular breakdowns of specific rubrics and feedback excerpts.
* **Trend & Trajectory Analysis**: Tracks trajectory over time (score growth across completed sessions).
* **Targeted Practice Recommendations**: Curates algorithms and LeetCode-style problems tailored to identified weak areas.
* **General Technical Inquiry**: Deep-dives into core concepts (e.g., Sliding Window, Monotonic Stacks, Union-Find, Binary Search On Answer Space) with invariants, templates, and 7-day study roadmaps.
* **Security & Guardrail Defense**: Strict boundary enforcement against prompt injection, roleplay jailbreaks, and out-of-scope queries.

---

## 🏗️ Architecture & Technology Stack

```
AI-Interview/
├── backend/                  # FastAPI Asynchronous Backend
│   ├── agents/               # Multi-agent logic (Interview, Evaluator, Hermes Mentor, State Extractor)
│   ├── core/                 # Auth, security, JWT, dependencies
│   ├── database/             # Async SQLite engine & table definitions
│   ├── models/               # SQLAlchemy ORM models (User, Session, Report, Coach)
│   ├── routers/              # API endpoints (Auth, Sessions, Reports, Coach)
│   ├── schemas/              # Pydantic v2 validation models
│   ├── services/             # Question loader, boilerplate, embeddings, evaluations
│   └── ws/                   # WebSocket real-time interview communications
├── frontend/                 # High-Performance Vanilla / Modern Web UI
│   ├── css/                  # Custom design system, glassmorphism, responsive grids
│   ├── js/                   # API client, WebSocket handlers, markdown renderer
│   ├── index.html            # Landing page & authentication portal
│   ├── dashboard.html        # Candidate launchpad & recent scorecard snapshot
│   ├── profile.html          # Dual-mode candidate profile (View Card & 4-step Wizard)
│   ├── interview.html        # Live interview workspace with code scratchpad
│   ├── history.html          # Session archives & on-demand report generation
│   ├── report.html           # 7-dimension scorecard & radar breakdown
│   └── coach.html            # Hermes AI Technical Mentor chat application
```

### Core Technologies
* **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) with asynchronous request pipelines (`asyncio`).
* **Database & Persistence**: [SQLite](https://www.sqlite.org/) with `SQLAlchemy` (2.0+) and `aiosqlite` async driver.
* **Vector Store & RAG**: [ChromaDB](https://www.trychroma.com/) with `SentenceTransformers` (`all-MiniLM-L6-v2`) for candidate scorecard chunking and retrieval.
* **LLM Engine**: [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index) (`mistralai/Mistral-7B-Instruct-v0.2`).
* **Real-Time Layer**: WebSockets for low-latency bidirectional message streaming and heartbeat pings.
* **Frontend**: Vanilla HTML5, modern ES6+ JavaScript, CSS3 Design Tokens, Tailwind CSS utilities, [Marked.js](https://marked.js.org/) for Markdown formatting.
* **Memory Architecture**: Dual-thread Windowed State Architecture with asynchronous background extraction workers (`state_extractor.py`) and 2-turn sliding window optimization.
* **Security**: JWT (HMAC-SHA256) access tokens, `passlib` bcrypt password hashing, CORS middleware.

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.10+** (Python 3.11 or 3.12 recommended)
* **Git**
* A free or pro [Hugging Face Access Token](https://huggingface.co/settings/tokens)

---

### Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/AI-Interview.git
   cd AI-Interview
   ```

2. **Create and Activate a Virtual Environment**:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(If `requirements.txt` is not present, install core packages: `pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings python-jose passlib bcrypt chromadb sentence-transformers huggingface_hub websockets python-multipart httpx`)*

4. **Configure Environment Variables**:
   Create a `.env` file in `backend/.env` or the project root:
   ```env
   APP_NAME="AI Interview Platform"
   DEBUG=True
   HOST=127.0.0.1
   PORT=8000

   # Hugging Face API Token (Required for AI Agents)
   HF_API_TOKEN=hf_your_huggingface_api_token_here
   HF_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2

   # JWT Security
   JWT_SECRET=super_secret_jwt_key_replace_for_production
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   REFRESH_TOKEN_EXPIRE_DAYS=7

   # Storage
   SQLITE_DB_PATH=ai_interview.db
   CHROMA_PERSIST_PATH=backend/chroma_data
   EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
   ```

5. **Start the Development Server**:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Access the Application**:
   Open your browser and navigate to:
   * **Web App**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * **Alternative API Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📖 Application Walkthrough

| View | Path | Description |
|---|---|---|
| **Landing & Auth** | `/` | Candidate sign-in and account registration. |
| **Dashboard** | `/dashboard` | Technical domain selection, mode picker, preferred language radio buttons (max 3/row), and latest session snapshot. |
| **Candidate Profile** | `/profile` | Dual-mode candidate profile: view mode summary and 4-step interactive wizard (personal info, target role, skills, preferences). |
| **Interview Workspace** | `/interview?session_id={id}` | Real-time chat with AI interviewer, collapsible code scratchpad, live countdown timer, and evaluation rubric preview. |
| **History** | `/history` | Searchable archive of all past interviews with status pills and on-demand report trigger. |
| **Scorecard Report** | `/report?interview_id={id}` | Deep evaluation across the 7 DSA metrics, strengths, weaknesses, Big-O summary, and detailed action points. |
| **Hermes Mentor** | `/coach` | Conversational mentorship interface with chat history management and dynamic topic breakdowns. |

---

## 🛡️ Security & Integrity Guardrails

* **Real Interview Protection**: Real-mode sessions detect page hides and disconnections via `navigator.sendBeacon` and terminate active sessions permanently to mirror real assessments.
* **Hermes Agent Jailbreak Defense**: Rejects attempts to bypass rules, exfiltrate system instructions, engage in out-of-scope roleplay, or provide direct code solutions without pedagogical guidance.
* **Token Isolation**: Session records and evaluation reports are strictly bound to authenticated candidate IDs via JWT claims.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
