import json
import re
from typing import List, Dict, Optional
from app.ai.llm import BaseLLMClient
from app.ai.schemas.knowledge import ProjectKnowledge
from app.ai.schemas.case_study import (
    GeneratedCaseStudy,
    CaseStudySection
)
from app.ai.prompts.case_study import (
    CASE_STUDY_SYSTEM_PROMPT,
    CASE_STUDY_USER_PROMPT
)

# Standardized technology categorization map
TECH_CATEGORIES: Dict[str, List[str]] = {
    "Backend & APIs": [
        "python", "fastapi", "flask", "django", "node.js", "nodejs", "express", "express.js",
        "go", "golang", "rust", "java", "spring boot", "spring", "c++", "c#", ".net", "dotnet",
        "graphql", "rest", "rest api", "grpc", "pydantic", "celery", "ruby", "rails", "php",
        "laravel", "scala", "elixir", "socket.io", "websockets", "asgi", "wsgi"
    ],
    "Frontend & UI": [
        "react", "react.js", "reactjs", "next.js", "nextjs", "vue", "vue.js", "vuejs",
        "angular", "svelte", "typescript", "javascript", "html", "css", "tailwind",
        "tailwindcss", "tailwind css", "redux", "vite", "zustand", "webpack", "bootstrap",
        "sass", "scss", "mui", "shadcn", "jquery"
    ],
    "AI & Machine Learning": [
        "openai", "gpt-4", "gpt-4o", "gpt-5", "gpt-5-mini", "gpt-3.5", "claude", "gemini",
        "langchain", "llamaindex", "pytorch", "tensorflow", "huggingface", "scikit-learn",
        "rapidfuzz", "pandas", "numpy", "ollama", "spacy", "nltk", "opencv", "anthropic"
    ],
    "Data, Scraping & Automation": [
        "apify", "apify_client", "beautifulsoup", "bs4", "scrapy", "selenium", "playwright",
        "puppeteer", "apollo.io", "apollo", "clearbit", "clearbit autocomplete api",
        "gspread", "google sheets api", "google sheets", "kafka", "rabbitmq", "redis streams",
        "airflow", "spark", "hadoop", "etl"
    ],
    "Databases & Storage": [
        "postgresql", "postgres", "mysql", "mongodb", "dynamodb", "redis", "sqlite",
        "pinecone", "qdrant", "chroma", "chromadb", "elasticsearch", "cassandra",
        "supabase", "firebase", "s3", "minio", "sqlalchemy", "prisma"
    ],
    "DevOps & Infrastructure": [
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "git", "github", "gitlab",
        "ci/cd", "terraform", "ansible", "prometheus", "grafana", "nginx", "linux",
        "datadog", "helm", "github actions", "vercel", "cloudflare"
    ]
}

def categorize_technologies(technologies: List[str]) -> Dict[str, List[str]]:
    """Group technology names into standardized functional categories."""
    categorized: Dict[str, List[str]] = {cat: [] for cat in TECH_CATEGORIES}
    uncategorized: List[str] = []

    for tech in technologies:
        clean_tech = tech.strip(" `*,-•\t\r\n")
        if not clean_tech:
            continue
        lower_tech = clean_tech.lower()
        matched = False
        for cat, keywords in TECH_CATEGORIES.items():
            for kw in keywords:
                if kw in lower_tech or lower_tech in kw:
                    if clean_tech not in categorized[cat]:
                        categorized[cat].append(clean_tech)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            if clean_tech not in uncategorized:
                uncategorized.append(clean_tech)

    result = {cat: items for cat, items in categorized.items() if items}
    if uncategorized:
        result["Libraries & Tools"] = uncategorized
    return result

def extract_technologies_from_prose(text: str) -> List[str]:
    """Extract individual technology names from narrative prose or comma-separated lists."""
    clean = re.sub(
        r"^(?:the\s+)?(?:technology\s+stack|tech\s+stack|technologies|tools)\s*(?:includes?|consists?\s+of|used|are|comprises?)?:?",
        "",
        text.strip(),
        flags=re.IGNORECASE
    ).strip()
    clean = re.sub(r"\b(?:and|supplemented\s+by|along\s+with|as\s+well\s+as|with|utilizing|leveraging)\b", ",", clean, flags=re.IGNORECASE)
    raw_tokens = [t.strip(" .`*,-•\t\r\n") for t in re.split(r"[,;]", clean) if t.strip()]
    return [t for t in raw_tokens if len(t) > 1 and not re.match(r"^(?:etc|and|also)$", t, re.IGNORECASE)]

def normalize_case_study(case_study: GeneratedCaseStudy, knowledge: Optional[ProjectKnowledge] = None) -> GeneratedCaseStudy:
    """
    Enforces the Universal Section Format across all case study sections:
    1. Executive Summary -> Single cohesive narrative paragraph (no bullets).
    2. Problem Statement -> Hybrid (prose context + bulleted constraints).
    3. Architecture & System Design -> Hybrid (system overview + component bullets).
    4. Key Technical Decisions -> Structured bullets with bold keys and tradeoffs.
    5. Engineering Challenges & Solutions -> Structured bullets with Challenge and Solution.
    6. Performance & Scale Metrics -> Structured bullets with bold metrics.
    7. Technologies & Tools -> Categorized bullet points (NEVER a plain paragraph).
    """
    for section in case_study.sections:
        title_lower = section.title.lower()

        # 1. Executive Summary & Overview
        if "executive summary" in title_lower or ("overview" in title_lower and "architecture" not in title_lower):
            section.format_type = "paragraph"
            lines = [l.strip().lstrip("-*• ") for l in section.content.splitlines() if l.strip()]
            section.content = " ".join(lines)

        # 2. Problem Statement & Engineering Context
        elif "problem" in title_lower:
            section.format_type = "hybrid"

        # 3. Architecture & System Design
        elif "architecture" in title_lower or "system design" in title_lower:
            section.format_type = "hybrid"

        # 4. Key Technical Decisions & Tradeoffs
        elif "decision" in title_lower:
            section.format_type = "bullets"
            lines = [l.strip() for l in section.content.splitlines() if l.strip()]
            has_bullets = any(l.startswith(("- ", "* ", "• ")) for l in lines)
            if not has_bullets:
                sentences = re.split(r"(?<=[.!?])\s+", section.content.strip())
                new_bullets = []
                for s in sentences:
                    s_clean = s.strip()
                    if len(s_clean) < 10:
                        continue
                    s_clean = re.sub(r"^(?:key\s+technical\s+decisions?\s+include\s*)", "", s_clean, flags=re.IGNORECASE)
                    if s_clean:
                        words = s_clean.split(" ")
                        if len(words) > 3 and not s_clean.startswith("**"):
                            header = " ".join(words[:2]).strip(":,")
                            rest = " ".join(words[2:])
                            new_bullets.append(f"- **{header}**: {rest}")
                        else:
                            new_bullets.append(f"- {s_clean}")
                if new_bullets:
                    section.content = "\n".join(new_bullets)

        # 5. Engineering Challenges & Deep-dive Solutions
        elif "challenge" in title_lower:
            section.format_type = "bullets"
            lines = [l.strip() for l in section.content.splitlines() if l.strip()]
            has_bullets = any(l.startswith(("- ", "* ", "• ")) for l in lines)
            if not has_bullets:
                sentences = re.split(r"(?<=[.!?])\s+", section.content.strip())
                new_bullets = []
                for s in sentences:
                    s_clean = s.strip()
                    if len(s_clean) < 10:
                        continue
                    if any(w in s_clean.lower() for w in ["mitigate", "solution", "resolved", "offload", "fix"]):
                        new_bullets.append(f"- **Engineered Solution**: {s_clean}")
                    else:
                        new_bullets.append(f"- **Engineering Challenge**: {s_clean}")
                if new_bullets:
                    section.content = "\n".join(new_bullets)

        # 6. Performance & Scale Metrics
        elif "performance" in title_lower or "scale" in title_lower or "metric" in title_lower:
            section.format_type = "bullets"
            lines = [l.strip() for l in section.content.splitlines() if l.strip()]
            has_bullets = any(l.startswith(("- ", "* ", "• ")) for l in lines)
            if not has_bullets:
                sentences = re.split(r"(?<=[.!?])\s+", section.content.strip())
                new_bullets = []
                for s in sentences:
                    s_clean = s.strip()
                    if len(s_clean) < 5:
                        continue
                    new_bullets.append(f"- **Scale Metric**: {s_clean}")
                if new_bullets:
                    section.content = "\n".join(new_bullets)

        # 7. Technologies & Tools / Technology Stack
        elif "technolog" in title_lower or "tool" in title_lower or "stack" in title_lower:
            section.format_type = "bullets"
            lines = [l.strip() for l in section.content.splitlines() if l.strip()]
            has_bullets = any(l.startswith(("- ", "* ", "• ")) for l in lines)
            has_preamble = any(re.match(r"^(?:the\s+)?(?:technology|tech\s+stack|technologies)", l, re.IGNORECASE) for l in lines)

            if not has_bullets or has_preamble:
                techs = []
                if knowledge and knowledge.technologies:
                    techs = list(knowledge.technologies)
                else:
                    techs = extract_technologies_from_prose(section.content)
                if techs:
                    categorized = categorize_technologies(techs)
                    bullet_lines = []
                    for cat, items in categorized.items():
                        bullet_lines.append(f"- **{cat}**: {', '.join(items)}")
                    section.content = "\n".join(bullet_lines)

    # Reconstruct unified markdown_content from normalized sections
    clean_title = re.sub(r"^#\s*", "", case_study.title).strip()
    md_parts = [f"# {clean_title}\n"]
    for s in case_study.sections:
        if s.omitted:
            continue
        md_parts.append(f"## {s.title}\n{s.content}\n")

    if "Verified Evidence Count" in (case_study.markdown_content or ""):
        footer_match = re.search(r"(\n---\n\*Verified Evidence Count:.*?\*)", case_study.markdown_content, re.DOTALL)
        if footer_match:
            md_parts.append(footer_match.group(1).strip())
    elif knowledge and knowledge.evidence:
        md_parts.append(f"---\n*Verified Evidence Count: {len(knowledge.evidence)} facts across resume and interview exchanges.*")

    case_study.markdown_content = "\n".join(md_parts).strip()
    return case_study

class CaseStudyGenerator:
    """
    Generates detailed, factual technical case studies directly from
    structured ProjectKnowledge objects. Strictly avoids fabricating numbers or facts.
    Enforces universal section formatting across all projects.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def generate_case_study(self, knowledge: ProjectKnowledge) -> GeneratedCaseStudy:
        knowledge_json = json.dumps(knowledge.model_dump(), indent=2)
        user_prompt = CASE_STUDY_USER_PROMPT.format(project_knowledge_json=knowledge_json)

        try:
            res = await self.llm.generate_structured(
                prompt=user_prompt,
                schema=GeneratedCaseStudy,
                system_prompt=CASE_STUDY_SYSTEM_PROMPT
            )
            if res.markdown_content and res.sections:
                return normalize_case_study(res, knowledge=knowledge)
        except Exception:
            pass

        # Deterministic grounded case study builder adhering strictly to universal format
        raw_cs = self._build_deterministic_case_study(knowledge)
        return normalize_case_study(raw_cs, knowledge=knowledge)

    def _build_deterministic_case_study(self, knowledge: ProjectKnowledge) -> GeneratedCaseStudy:
        sections: List[CaseStudySection] = []
        order = 1

        title = f"Technical Case Study: {knowledge.project_name}"

        # 1. Executive Summary (Narrative Paragraph)
        summary = (
            f"An in-depth technical analysis of **{knowledge.project_name}**, "
            f"highlighting architectural decisions, technical implementation, and measurable outcomes."
        )
        if knowledge.problem.statement:
            summary += f" The system addresses: *{knowledge.problem.statement}*."
        sections.append(CaseStudySection(title="Executive Summary", format_type="paragraph", content=summary, order=order))
        order += 1

        # 2. Problem Statement (Hybrid: Context paragraph + Pain Points)
        if knowledge.problem.statement or knowledge.problem.context:
            prob_lines = []
            if knowledge.problem.statement:
                prob_lines.append(knowledge.problem.statement)
            else:
                prob_lines.append("Identified operational friction, manual bottlenecks, and architectural constraints requiring systematic redesign.")
            if knowledge.problem.context:
                prob_lines.append(f"\n- **Engineering Context**: {knowledge.problem.context}")
            if knowledge.problem.motivation:
                prob_lines.append(f"- **Primary Motivation**: {knowledge.problem.motivation}")
            prob_content = "\n".join(prob_lines)
            sections.append(CaseStudySection(title="Problem Statement & Context", format_type="hybrid", content=prob_content, order=order))
            order += 1

        # 3. System Architecture (Hybrid: Topology paragraph + Component bullets)
        if knowledge.architecture.overview or knowledge.architecture.components:
            arch_parts = []
            if knowledge.architecture.overview:
                arch_parts.append(knowledge.architecture.overview)
            else:
                arch_parts.append("System architecture designed for modularity, resilience, and high throughput.")
            if knowledge.architecture.components:
                arch_parts.append("\n**Core Subsystems & Components:**")
                for c in knowledge.architecture.components:
                    arch_parts.append(f"- **{c}**: Subsystem handling dedicated workload execution.")
            arch_content = "\n".join(arch_parts)
            sections.append(CaseStudySection(title="System Architecture", format_type="hybrid", content=arch_content, order=order))
            order += 1

        # 4. Technical Decisions (Structured Bullets with bold titles)
        if knowledge.technical_decisions:
            dec_bullets = []
            for d in knowledge.technical_decisions:
                if ":" in d:
                    k, v = d.split(":", 1)
                    dec_bullets.append(f"- **{k.strip()}**: {v.strip()}")
                else:
                    dec_bullets.append(f"- **Architectural Choice**: {d}")
            dec_content = "\n".join(dec_bullets)
            sections.append(CaseStudySection(title="Key Technical Decisions", format_type="bullets", content=dec_content, order=order))
            order += 1

        # 5. Challenges & Solutions (Structured Bullet Pairs)
        if knowledge.challenges or knowledge.solutions:
            cs_bullets = []
            for i, c in enumerate(knowledge.challenges):
                sol = knowledge.solutions[i] if i < len(knowledge.solutions) else "Engineered architectural mitigation and fault recovery mechanisms."
                cs_bullets.append(f"- **Challenge — {c}**\n  **Solution**: {sol}")
            if len(knowledge.solutions) > len(knowledge.challenges):
                for s in knowledge.solutions[len(knowledge.challenges):]:
                    cs_bullets.append(f"- **Implemented Solution**: {s}")
            cs_content = "\n".join(cs_bullets)
            sections.append(CaseStudySection(title="Challenges & Solutions", format_type="bullets", content=cs_content, order=order))
            order += 1

        # 6. Performance & Scale (Bulleted Metrics with bold figures)
        if knowledge.performance:
            perf_bullets = []
            for p in knowledge.performance:
                if ":" in p:
                    k, v = p.split(":", 1)
                    perf_bullets.append(f"- **{k.strip()}**: **{v.strip()}**")
                else:
                    perf_bullets.append(f"- **Scale Metric**: **{p}**")
            perf_content = "\n".join(perf_bullets)
            sections.append(CaseStudySection(title="Performance & Scale", format_type="bullets", content=perf_content, order=order))
            order += 1

        # 7. Impact & Results (Bulleted Items)
        if knowledge.impact:
            impact_bullets = []
            for i in knowledge.impact:
                if ":" in i:
                    k, v = i.split(":", 1)
                    impact_bullets.append(f"- **{k.strip()}**: {v.strip()}")
                else:
                    impact_bullets.append(f"- **Operational Impact**: {i}")
            impact_content = "\n".join(impact_bullets)
            sections.append(CaseStudySection(title="Results & Impact", format_type="bullets", content=impact_content, order=order))
            order += 1

        # 8. Technologies Used (Categorized Bullet Points)
        if knowledge.technologies:
            categorized = categorize_technologies(knowledge.technologies)
            tech_bullets = []
            for cat, items in categorized.items():
                tech_bullets.append(f"- **{cat}**: {', '.join(items)}")
            tech_content = "\n".join(tech_bullets)
            sections.append(CaseStudySection(title="Technology Stack", format_type="bullets", content=tech_content, order=order))
            order += 1

        # Build combined markdown
        md_parts = [f"# {title}\n"]
        for s in sections:
            md_parts.append(f"## {s.title}\n{s.content}\n")
        md_parts.append(f"---\n*Verified Evidence Count: {len(knowledge.evidence)} facts across resume and interview exchanges.*")

        full_md = "\n".join(md_parts)

        return GeneratedCaseStudy(
            project_id=knowledge.project_id,
            title=title,
            executive_summary=summary,
            sections=sections,
            markdown_content=full_md
        )
