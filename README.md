# Resume-to-Technical-Case-Study System

An AI-orchestrated, backend-first system that ingests arbitrary resumes (PDF, DOCX, TXT), detects technical engineering projects without template constraints, conducts an adaptive interview to fill gaps, tracks project knowledge with provenance, and generates high-fidelity technical case studies.

## Deployed Environments

- **Frontend**: [https://resume-project-sooty-eta.vercel.app/](https://resume-project-sooty-eta.vercel.app/)
- **Backend API**: [https://resume-project-gye0.onrender.com/](https://resume-project-gye0.onrender.com/)
- **Backend Docs**: [https://resume-project-gye0.onrender.com/docs](https://resume-project-gye0.onrender.com/docs)

## Project Structure

```text
Resume_project/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── config.py                # App configuration & settings
│   │   ├── api/                     # API routers and dependencies
│   │   ├── services/                # Parser, extractor, interview, case study
│   │   ├── ai/                      # Pluggable LLMs (Gemini, OpenAI, Mock) & prompts
│   │   ├── models/                  # SQLAlchemy 2.0 async models
│   │   └── repositories/            # Database repositories
│   ├── tests/                       # Pytest test suite
│   └── pyproject.toml               # Python project configuration
├── frontend/                        # Vite + React minimal UI
├── storage/                         # Local database and uploaded files
├── docs/                            # Architectural specifications
└── prompt.md                        # Original requirements document
```

## Quick Start

### 1. Backend Setup

From the `backend/` directory:

```bash
# Optional: Set up environment variables (.env)
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_key_here
# or LLM_PROVIDER=openai / OPENAI_API_KEY=your_key_here
# Defaults to "mock" mode if no API key is provided for instant offline use.

# Run database tests
uv run pytest tests -v

# Start FastAPI development server
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Frontend Setup

From the `frontend/` directory:

```bash
npm install
npm run dev
```

The UI will be accessible at [http://localhost:5173](http://localhost:5173).
