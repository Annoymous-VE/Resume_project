# Resume-to-Technical-Case-Study System Architecture

## Overview

The Resume-to-Technical-Case-Study system is a backend-first platform designed to extract technical projects from arbitrary resume formats, conduct an adaptive technical interview to deepen knowledge, and generate factual, grounded technical case studies.

```
Resume Upload (PDF / DOCX / TXT)
          ↓
  ResumeParser (Layout & Column aware)
          ↓
  DocumentRepresentation (Blocks with page, column, type)
          ↓
  ProjectExtractor (Semantic & structural extraction)
          ↓
  ProjectKnowledge (Fact provenance & evidence tracking)
          ↓
  InterviewEngine (Adaptive question selection & stopping conditions)
          ↓
  CaseStudyGenerator (Factual markdown generation)
```

## Layered Architecture

1. **API Layer (`backend/app/api/routes`)**
   - Clean FastAPI routers for Resumes, Projects, Interview sessions, and Case studies.
   - Decoupled from AI and business logic through Dependency Injection (`dependencies.py`).

2. **Domain & Services Layer (`backend/app/services`)**
   - `resume_parser.py`: Multi-format layout parser extracting columns, headings, and bullets.
   - `project_extractor.py`: Identifies project boundaries and attributes without template assumptions.
   - `knowledge_manager.py`: Manages facts with source provenance (`resume`, `user_answer_X`), computes coverage metrics (`UNKNOWN`, `PARTIAL`, `SUFFICIENT`).
   - `interview_engine.py`: Selects highest-value missing knowledge area, formulates targeted questions, and detects stopping criteria.
   - `case_study_generator.py`: Maps verified knowledge items into structured case study sections.

3. **AI Layer (`backend/app/ai`)**
   - `llm.py`: Pluggable LLM interface supporting Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o`), and deterministic `MockLLMClient`.
   - `prompts/`: Modular system prompts enforcing zero-hallucination policies.
   - `schemas/`: Pydantic v2 schemas for strict JSON structured outputs.

4. **Persistence Layer (`backend/app/repositories` & `backend/app/models`)**
   - Async SQLAlchemy 2.0 with SQLite / aiosqlite.
   - Distinct entity tables: `resumes`, `projects`, `interview_sessions`, `interview_exchanges`, `project_knowledge_records`, and `case_study_records`.

5. **Frontend Layer (`frontend/`)**
   - Lightweight React + Vite single-page application executing the complete user workflow.
