import urllib.request
import json
import base64
import os

os.makedirs('scratch/diagrams', exist_ok=True)

diagrams = {
    'flowchart': """
graph TD
    A["User Uploads Resume<br/>(PDF, DOCX, or TXT)"] --> B["Resume Parser<br/>Reads layout and structure"]
    B --> C["Project Detector<br/>Finds technical projects in resume"]
    C --> D{"Project Selection"}

    D -->|"Select detected project"| E["Select Detected Project<br/>From extracted catalog"]
    D -->|"Project not on resume?"| F["Add External Project<br/>Manual entry via form"]

    E --> G["Adaptive Interview Engine<br/>Targeted gap-filling Q&A"]
    F --> G

    G --> H{"Knowledge Gaps<br/>Remaining?"}
    H -->|"Yes"| I["Ask Targeted Question<br/>Focus on top missing dimension"]
    I --> J["Candidate Response<br/>User answers in own words"]
    J --> K["Knowledge Repository<br/>Provenance-tracked fact storage"]
    K --> H
    H -->|"No - Coverage Sufficient"| L["Case Study Generator<br/>Synthesizes verified facts"]
    L --> M["Final Case Study Deliverable<br/>Download as PDF, Word, or Markdown"]
""",
    'architecture': """
graph TB
    subgraph Browser ["User Interface - Browser"]
        UI["React Web Application<br/>(Vite + React 19)"]
    end
    
    subgraph Backend ["Backend Server - FastAPI (Python 3.12)"]
        API["API Routing Layer<br/>REST Endpoints"]
        subgraph Services ["Core Processing Services"]
            RP["Resume Parser<br/>Layout-aware document engine"]
            PE["Project Extractor<br/>Semantic + heuristic detection"]
            IE["Interview Engine<br/>Adaptive question selection"]
            KM["Knowledge Manager<br/>Provenance-tracked repository"]
            CSG["Case Study Generator<br/>Structured document synthesis"]
            CSE["Document Exporter<br/>PDF / DOCX layout engine"]
        end
        AI["AI Abstraction Layer<br/>Pluggable LLM interface"]
        DB["Data Access Layer<br/>Asynchronous repositories"]
    end
    
    subgraph Providers ["AI Providers (Interchangeable)"]
        GEM["Google Gemini"]
        OAI["OpenAI GPT"]
        MOCK["Mock Engine<br/>(Offline Mode)"]
    end
    
    subgraph Persistence ["Persistence Layer"]
        SQLITE["SQLite Database<br/>Structured relational data"]
        FILES["Filesystem Storage<br/>Source files & exported docs"]
    end
    
    UI <-->|"HTTP REST API"| API
    API --> RP & PE & IE & KM & CSG & CSE
    PE & IE & CSG --> AI
    AI --> GEM & OAI & MOCK
    RP & PE & IE & KM & CSG --> DB
    DB --> SQLITE & FILES
""",
    'er_diagram': """
erDiagram
    RESUME ||--o{ PROJECT : "has many"
    PROJECT ||--o| INTERVIEW_SESSION : "has one"
    INTERVIEW_SESSION ||--o{ INTERVIEW_EXCHANGE : "has many Q&A pairs"
    PROJECT ||--o| PROJECT_KNOWLEDGE : "has one"
    PROJECT ||--o| CASE_STUDY : "has one"

    RESUME {
        string id PK
        string filename
        string file_path
        string file_type
        json raw_structure
        datetime created_at
    }
    PROJECT {
        string id PK
        string resume_id FK
        string name
        text description
        json data_json
        float confidence
        datetime created_at
    }
    INTERVIEW_SESSION {
        string id PK
        string project_id FK
        string status
        int round_count
        json coverage_json
        string stop_reason
        datetime created_at
        datetime updated_at
    }
    INTERVIEW_EXCHANGE {
        string id PK
        string session_id FK
        string question_id
        string target_area
        text question
        text answer
        datetime created_at
        datetime answered_at
    }
    PROJECT_KNOWLEDGE {
        string id PK
        string project_id FK
        json knowledge_json
        datetime updated_at
    }
    CASE_STUDY {
        string id PK
        string project_id FK
        string title
        text markdown_content
        json sections_json
        datetime created_at
    }
"""
}

for name, code in diagrams.items():
    obj = {
        'code': code.strip(),
        'mermaid': {
            'theme': 'neutral',
            'themeVariables': {
                'fontFamily': 'Helvetica, Arial, sans-serif',
                'fontSize': '14px',
                'primaryColor': '#F1F5F9',
                'primaryBorderColor': '#0284C7',
                'lineColor': '#0284C7'
            }
        }
    }
    encoded = base64.urlsafe_b64encode(json.dumps(obj).encode('utf-8')).decode('ascii').rstrip('=')
    url = f'https://mermaid.ink/img/{encoded}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            out_path = f'scratch/diagrams/{name}.png'
            with open(out_path, 'wb') as f:
                f.write(data)
            print(f'Successfully downloaded {name} ({len(data)} bytes) to {out_path}')
    except Exception as e:
        print(f'Failed {name}:', e)
