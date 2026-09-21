# Resume-to-Technical-Case-Study System
## Build Specification for Google Antigravity

## 1. Goal

Build a backend-first system that takes an arbitrary resume, extracts the technical projects mentioned in it regardless of the resume template/layout, conducts a short adaptive interview to gather missing technical depth, stores the resulting project knowledge in a structured form, and generates a detailed technical case study.

The frontend is intentionally minimal. The backend, AI workflow, data model, maintainability, and extensibility are the priorities.

The system must NOT depend on fixed resume templates or assume that a section is literally called "Projects".

---

# 2. Core Product Workflow

```text
Resume Upload
    ↓
Document Parsing
    ↓
Layout-aware / structure-aware representation
    ↓
Semantic Section Identification
    ↓
Project Detection & Extraction
    ↓
Normalized Project Objects
    ↓
Initial High-value Questions
    ↓
User Answers
    ↓
Knowledge / Coverage Update
    ↓
Identify Highest-value Missing Information
    ↓
Ask ONE targeted follow-up question
    ↓
Repeat until sufficient coverage
    ↓
Project Knowledge Object
    ↓
Case Study Generation
    ↓
Final Technical Case Study
```

The system should optimize for **maximum useful information with minimum questions**.

Do NOT implement a long fixed questionnaire.

---

# 3. Resume Understanding

## Requirement

Users may use completely different resume templates:

- One-column
- Two-column
- Custom designs
- Different heading names
- Projects mixed with experience
- Projects without an explicit "Projects" heading
- Different bullet structures
- Different ordering of information

Template/layout must therefore NOT be the primary extraction strategy.

## Correct approach

Use:

```text
Document structure
+
Text
+
Formatting/layout relationships
+
Semantic understanding
```

The extractor should identify entities that represent technical/software projects based on their content and context.

Possible section names include:

- Projects
- Personal Projects
- Academic Projects
- Selected Work
- Featured Work
- Relevant Work

But these names are only signals, not requirements.

---

# 4. Internal Resume Representation

Convert the uploaded document into a normalized representation before project extraction.

Conceptually:

```json
{
  "document": {
    "metadata": {},
    "blocks": [
      {
        "id": "block_1",
        "type": "heading",
        "text": "Selected Projects",
        "order": 1,
        "page": 1,
        "column": 1
      },
      {
        "id": "block_2",
        "type": "bullet",
        "text": "...",
        "order": 2,
        "page": 1,
        "column": 1
      }
    ]
  }
}
```

The exact implementation can vary, but preserve enough structure to reason about document relationships.

---

# 5. Project Extraction

Each detected project should be normalized into a common schema.

```json
{
  "id": "project_id",
  "name": "",
  "description": "",
  "technologies": [],
  "contributions": [],
  "outcomes": [],
  "links": [],
  "source_blocks": [],
  "confidence": 0.0
}
```

Missing information should be represented as empty/null rather than invented.

The extractor must distinguish:

- Explicit resume facts
- Inferred information
- Unknown information

Do not hallucinate project details.

---

# 6. Project Knowledge Model

Do NOT store knowledge only as final case-study sections.

The source of truth should be a structured **Project Knowledge Object**.

Case-study sections are a presentation layer generated from this knowledge.

Recommended structure:

```json
{
  "project": {},

  "problem": {
    "statement": "",
    "context": "",
    "motivation": ""
  },

  "requirements": [],

  "architecture": {
    "overview": "",
    "components": [],
    "data_flow": ""
  },

  "technical_decisions": [],

  "implementation": [],

  "challenges": [],

  "solutions": [],

  "tradeoffs": [],

  "performance": [],

  "impact": [],

  "technologies": [],

  "evidence": []
}
```

Each important knowledge item should retain provenance.

Example:

```json
{
  "fact": "Redis was used for caching",
  "source": "user_answer_7",
  "confidence": 0.94
}
```

The system should be able to determine where information came from.

---

# 7. Adaptive Interview Engine

The interview must NOT be a rigid questionnaire.

Start with approximately 3–5 high-value questions covering areas such as:

1. Problem — What were you solving and why?
2. Architecture — How did you design/build it?
3. Technical decisions — Why did you choose this approach?
4. Challenges — What went wrong and how did you solve it?
5. Impact — What measurable result did it produce?

Then analyze the answer.

Example:

User:

> "Used Redis for caching."

Knowledge:

```text
Redis used for caching     ✓
What was cached?           ?
Why Redis?                 ?
Performance improvement?   ?
```

Ask one targeted question that provides the highest-value missing information.

Do not ask several redundant questions at once.

---

# 8. Question Selection Strategy

The interview engine should conceptually optimize:

> Which single question will improve the final case study the most?

Use an information-coverage model.

Each project knowledge area should have a coverage state such as:

```text
UNKNOWN
PARTIAL
SUFFICIENT
```

Example:

```json
{
  "architecture": "SUFFICIENT",
  "technical_decisions": "PARTIAL",
  "challenges": "UNKNOWN",
  "impact": "SUFFICIENT"
}
```

The next question should target the highest-value unresolved area.

---

# 9. Interview Stopping Conditions

Do not continue indefinitely.

Stop when one or more of the following is true:

- Required knowledge areas have sufficient coverage.
- Remaining unknowns are low-value.
- Additional questions have low expected information gain.
- The project can already produce a strong case study.
- The user explicitly chooses to finish.

The goal is **information density, not number of questions**.

---

# 10. Case Study Generation

The generator consumes the Project Knowledge Object.

It should NOT depend directly on raw interview transcripts.

Conceptually:

```text
Project Knowledge
       ↓
Section Selection
       ↓
Section Generation
       ↓
Technical Case Study
```

Use a fixed set of possible case-study sections, but allow sections to be omitted when they are not relevant or sufficiently supported.

Do not fabricate content simply to fill a section.

---

# 11. Suggested Case Study Sections

Keep the system extensible so the exact section set can evolve.

Potential sections include:

```text
1. Project Overview
2. Problem & Motivation
3. Architecture / System Design
4. Technical Implementation
5. Key Technical Decisions
6. Challenges & Solutions
7. Performance / Optimization
8. Results / Impact
9. Technology Stack
```

Not every project needs every section.

---

# 12. Backend Architecture

Use a simple layered architecture:

```text
API
 ↓
Services
 ↓
AI / Domain Logic
 ↓
Repositories
 ↓
Database
```

Do not put business logic or LLM logic directly inside API routes.

---

# 13. Folder Structure

Implement approximately:

```text
resume-case-study/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── resume.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── interview.py
│   │   │   │   └── case_study.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── services/
│   │   │   ├── resume_parser.py
│   │   │   ├── project_extractor.py
│   │   │   ├── interview_engine.py
│   │   │   ├── knowledge_manager.py
│   │   │   └── case_study_generator.py
│   │   │
│   │   ├── ai/
│   │   │   ├── llm.py
│   │   │   ├── prompts/
│   │   │   │   ├── project_extraction.py
│   │   │   │   ├── question_generation.py
│   │   │   │   └── case_study.py
│   │   │   └── schemas/
│   │   │       ├── project.py
│   │   │       ├── knowledge.py
│   │   │       └── question.py
│   │   │
│   │   ├── models/
│   │   │   ├── project.py
│   │   │   ├── interview.py
│   │   │   └── case_study.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── project_repository.py
│   │   │   ├── interview_repository.py
│   │   │   └── case_study_repository.py
│   │   │
│   │   └── utils/
│   │
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_extraction.py
│   │   ├── test_interview.py
│   │   └── test_generation.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/
│   └── package.json
│
├── storage/
│   ├── uploads/
│   └── generated/
│
├── docs/
│   └── architecture.md
│
├── .env
├── docker-compose.yml
└── README.md
```

Keep this structure pragmatic. Do not create unnecessary microservices.

---

# 14. Module Responsibilities

### `resume_parser.py`

Responsibilities:

- Accept supported resume files.
- Extract text and structural information.
- Normalize document representation.
- Preserve source references.

It should be possible to replace the parser later.

### `project_extractor.py`

Responsibilities:

- Identify project candidates.
- Determine project boundaries.
- Extract initial project facts.
- Produce normalized Project objects.
- Preserve source references and confidence.

### `interview_engine.py`

Responsibilities:

- Track current project knowledge.
- Determine missing information.
- Select the next highest-value question.
- Evaluate answers.
- Decide when to stop.

### `knowledge_manager.py`

Responsibilities:

- Merge new information into Project Knowledge.
- Avoid losing previous information.
- Track provenance.
- Track confidence.
- Track coverage.

### `case_study_generator.py`

Responsibilities:

- Select relevant sections.
- Generate sections from structured knowledge.
- Avoid unsupported claims.
- Produce final case study.

### `ai/`

Responsibilities:

- LLM provider abstraction.
- Prompt management.
- Structured LLM outputs.
- AI-specific schemas.

The LLM provider should be replaceable.

### `repositories/`

Responsibilities:

- Persistence only.
- No AI/business logic.

---

# 15. API Design

Create clean APIs approximately like:

```text
POST   /api/resumes
GET    /api/projects
GET    /api/projects/{project_id}

POST   /api/projects/{project_id}/interview/start
POST   /api/projects/{project_id}/interview/answer
GET    /api/projects/{project_id}/interview/status

GET    /api/projects/{project_id}/knowledge

POST   /api/projects/{project_id}/case-study/generate
GET    /api/projects/{project_id}/case-study
```

Exact endpoint names may be adjusted if the implementation benefits from it.

---

# 16. Minimal Frontend

The frontend is NOT the focus.

It only needs to demonstrate:

```text
Upload Resume
      ↓
Show Detected Projects
      ↓
Select Project
      ↓
Display Question
      ↓
Enter Answer
      ↓
Display Next Question
      ↓
Generate Case Study
      ↓
Display Result
```

Keep styling minimal.

Do not spend significant development effort on visual design.

---

# 17. Persistence

Use a relational database or similarly structured persistent store.

At minimum model:

```text
Resume
Project
InterviewSession
InterviewQuestion
InterviewAnswer
ProjectKnowledge
CaseStudy
```

The exact database technology can be chosen for simplicity and maintainability.

Store uploaded files separately from structured application data.

---

# 18. Important Engineering Requirements

### Separation of concerns

Keep these independent:

```text
Parsing
Extraction
Interview
Knowledge
Generation
Persistence
API
```

### Replaceability

It should be easy to replace:

- LLM provider
- Resume parser
- Database
- Prompt
- Question-selection strategy
- Case-study format

### Structured AI output

Prefer structured/schema-validated LLM responses over parsing arbitrary prose from model output.

### No hallucination

Never invent:

- Technologies
- Metrics
- Architecture
- Responsibilities
- Performance numbers
- Business impact

If information is unknown, mark it unknown.

### Provenance

Important facts should retain their source.

Possible source types:

```text
resume
user_answer
system_inference
```

System inference must be clearly distinguished from user-provided facts.

---

# 19. Testing Strategy

Prioritize backend tests.

Test:

### Resume parsing

- Different layouts
- Multiple columns
- Different headings
- Projects without a Projects heading

### Project extraction

- Multiple projects
- Ambiguous project boundaries
- Missing fields
- Non-project experience

### Interview

- Initial questions
- Follow-up selection
- Knowledge updates
- Stopping conditions
- Avoiding redundant questions

### Generation

- Complete project
- Partially documented project
- Missing metrics
- Missing architecture
- Irrelevant sections

---

# 20. Development Priorities

Implement in this order:

```text
1. Project/domain schemas
2. Resume parsing
3. Project extraction
4. Persistence
5. Knowledge manager
6. Interview engine
7. LLM integration
8. Case-study generation
9. API integration
10. Minimal frontend
11. Tests
12. Documentation
```

Do not start by building the UI.

---

# 21. MVP Definition

The MVP is successful when:

1. A user uploads a resume.
2. The system can process different resume templates.
3. Technical projects are detected.
4. Each project is converted into a normalized structure.
5. The system asks a small number of meaningful questions.
6. Questions adapt based on previous answers.
7. The system stops when enough information is available.
8. Project knowledge is persisted separately from the final case study.
9. A detailed technical case study is generated.
10. Unsupported information is not fabricated.

---

# 22. Implementation Philosophy

Prefer:

- Simple
- Modular
- Typed
- Testable
- Observable
- Easy to modify

Avoid:

- Premature microservices
- Over-engineering
- Large framework abstractions without need
- Fixed resume-template assumptions
- Fixed interview questionnaires
- Mixing prompts throughout business logic
- LLM calls directly from route handlers

Build a clean MVP first, while keeping the boundaries clear enough to extend later.

---

# 23. Deliverables

Create:

```text
- Complete backend
- Minimal frontend
- Database models/migrations
- AI schemas
- Prompt files
- API endpoints
- Tests
- README
- Architecture documentation
- Environment configuration example
- Docker configuration if appropriate
```

The generated project should run locally with clear setup instructions.

Before implementation, inspect the architecture and identify any obvious inconsistencies or missing dependencies. Resolve them with the simplest maintainable design rather than adding unnecessary complexity.
