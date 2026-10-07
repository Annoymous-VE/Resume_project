# Future Enhancements & Action Plan (To-Do List)

This document outlines the priority roadmap and actionable implementation tasks for upcoming enhancements to the Resume-to-Technical-Case-Study system.

---

## 1. Client Brochure Case Study Generation

**Goal:** Expand system capabilities to generate client-facing brochure case studies (sales & marketing collateral) alongside deep technical engineering case studies.

### Implementation Checklist:
- [x] **Define Client Brochure Schema & Prompts** (COMPLETED)
  - Implement a new LLM prompt focused on high-level business value, executive summary, ROI, problem solved from the client perspective, and delivered capabilities.
  - Omit low-level code/infrastructure minutiae in favor of clear, non-technical language.
- [x] **Extend Database Schema (`backend/app/models/entities.py`)** (COMPLETED)
  - Update `CaseStudyRecord` to support multiple variants per project by introducing a `variant_type` field (`"technical"` vs. `"client_brochure"`).
  - Update `Project.case_study` relationship from one-to-one to one-to-many (`case_studies`).
- [x] **Design Brochure PDF / Document Template (`backend/app/services/case_study_exporter.py`)** (COMPLETED)
  - Implement a dedicated 1-to-2 page flyer/brochure PDF template using ReportLab.
  - Include visual metric callout boxes (e.g., efficiency gains, uptime, user scale), branded headers, and executive summary sidebars.
- [x] **Add Format Toggle in Frontend UI (`frontend/src/App.jsx`)** (COMPLETED)
  - Add an audience selector tab at Step 4: **[🛠️ Technical Case Study]** ↔ **[💼 Client Brochure]**.
  - Allow generating and previewing both versions independently from the same underlying knowledge ledger.

---

## 2. Proactive Obstacle & Resolution Inquiry Flow

**Goal:** Ensure the interview engine actively probes for real-world engineering obstacles, bottlenecks, and the specific technical measures taken to resolve them.

### Implementation Checklist:
- [x] **Enforce Mandatory Obstacle Phase-Gate (`backend/app/services/interview_engine.py`)** (COMPLETED)
  - Update `select_next_question()` so the interview cannot finish or terminate early until at least one concrete obstacle and its corresponding mitigation have been gathered.
- [x] **Implement Targeted Probing Prompts** (COMPLETED)
  - Refine question generation to explicitly ask:
    > *"In real-world engineering, virtually no system is built without friction. What were the key obstacles, architectural bottlenecks, or failure modes you encountered, and what specific measures did you take to overcome them?"*
- [x] **Build Fallback Escalation for Superficial Answers** (COMPLETED)
  - Add detection for dismissive or non-informative replies (e.g., *"everything went smoothly"*).
  - Automatically follow up with category prompts: *"Even well-designed architectures face constraints like API rate limits, database locks, slow queries, or third-party integration bugs. Which of these did you experience?"*
- [x] **Extract & Store Structured Obstacle-Mitigation Pairs (`backend/app/services/knowledge_manager.py`)** (COMPLETED)
  - Update the knowledge extraction pass to store challenges as structured pairs:
    - `obstacle`: Description of the roadblock/issue.
    - `root_cause`: Underlying technical cause.
    - `measures_taken`: Architectural or code changes applied.
    - `outcome`: Measured result after resolution.

---

## 3. User Credentials & Personal Dashboard

**Goal:** Provide secure user authentication and a centralized dashboard where users can manage their previous resumes, interviews, and generated case studies.

### Implementation Checklist:
- [x] **Implement Backend Authentication & Security (`backend/app/api/`)** (COMPLETED)
  - Create dedicated auth routes (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`).
  - Implement JWT token generation, refresh tokens, and password hashing using Argon2 or Bcrypt.
- [x] **Multi-Tenancy & Data Isolation (`backend/app/models/entities.py`)** (COMPLETED)
  - Add a `User` entity (`id`, `email`, `hashed_password`, `full_name`, `created_at`).
  - Add `user_id` foreign keys to `Resume` and `Project` models.
  - Enforce user-level tenancy across all database repositories and API routes.
- [x] **Build Authentication Frontend Components (`frontend/src/`)** (COMPLETED)
  - Create responsive Login and Sign-Up modals/pages with secure token storage (HTTP-only cookies or secure localStorage).
  - Add route guarding and active session state management.
- [x] **Build Centralized User Dashboard View** (COMPLETED)
  - **Resume History:** View and manage previously uploaded documents; re-extract projects without re-uploading.
  - **Case Study Archive:** Access, preview, and download previously generated technical case studies and client brochures.
  - **Interview Transcripts:** Review past interview sessions and resume incomplete interviews from where they left off.
  - **Search & Filter:** Filter projects by name, status, or technology stack.
