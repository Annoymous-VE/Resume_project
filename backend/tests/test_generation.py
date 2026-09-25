import pytest
from app.ai.llm import MockLLMClient
from app.services.knowledge_manager import KnowledgeManager
from app.services.case_study_generator import CaseStudyGenerator
from app.ai.schemas.project import ExtractedProject

@pytest.mark.asyncio
async def test_case_study_generation():
    llm = MockLLMClient()
    km = KnowledgeManager()
    generator = CaseStudyGenerator(llm)

    proj = ExtractedProject(
        id="proj_val",
        name="Distributed Cache Proxy",
        description="High-performance L7 caching proxy",
        technologies=["Rust", "Redis", "Tokio"],
        contributions=["Engineered non-blocking connection pool"],
        outcomes=["Handled 100k req/s at p99 2ms"]
    )

    knowledge = km.initialize_knowledge(proj)
    knowledge.technical_decisions.append("Chose Rust for memory safety and zero-cost abstractions over Go.")
    knowledge.challenges.append("Encountered thread contention on shared ring buffers.")
    knowledge.solutions.append("Refactored to per-core thread-pinned queues with lock-free atomics.")

    case_study = await generator.generate_case_study(knowledge)
    assert case_study.project_id == "proj_val"
    assert "Distributed Cache Proxy" in case_study.title
    assert len(case_study.sections) >= 4
    assert "Executive Summary" in [s.title for s in case_study.sections]
    assert "Key Technical Decisions" in [s.title for s in case_study.sections]
    assert "Rust" in case_study.markdown_content

    # Verify universal formatting adherence
    sec_map = {s.title: s for s in case_study.sections}
    assert sec_map["Executive Summary"].format_type == "paragraph"
    assert not sec_map["Executive Summary"].content.startswith("- ")

    assert sec_map["Technology Stack"].format_type == "bullets"
    assert "- **" in sec_map["Technology Stack"].content
    assert "Rust" in sec_map["Technology Stack"].content

    assert sec_map["Key Technical Decisions"].format_type == "bullets"
    assert sec_map["Key Technical Decisions"].content.startswith("- ")


@pytest.mark.asyncio
async def test_normalize_unbulleted_technology_paragraph():
    """Verify that unbulleted paragraphs in Technologies & Tools are automatically normalized into categorized bullets."""
    from app.services.case_study_generator import normalize_case_study
    from app.ai.schemas.case_study import GeneratedCaseStudy, CaseStudySection

    unbulleted_tech_text = (
        "The technology stack includes Python, FastAPI, React.js, Apollo.io, Apify, "
        "and Git/GitHub, supplemented by OpenAI gpt-5-mini, Clearbit Autocomplete API, RapidFuzz, and gspread."
    )

    raw_cs = GeneratedCaseStudy(
        project_id="test_proj",
        title="AI-Enabled Lead Generation Pipeline",
        executive_summary="Executive summary text.",
        sections=[
            CaseStudySection(
                title="Executive Summary & Overview",
                content="This case study details the design, architecture, and metrics.",
                order=1
            ),
            CaseStudySection(
                title="Technologies & Tools",
                content=unbulleted_tech_text,
                order=2
            )
        ],
        markdown_content="Initial text"
    )

    normalized = normalize_case_study(raw_cs)
    tech_sec = [s for s in normalized.sections if "technolog" in s.title.lower()][0]

    # Verify converted to categorized bullets
    assert tech_sec.format_type == "bullets"
    assert "- **Backend & APIs**:" in tech_sec.content
    assert "Python" in tech_sec.content
    assert "FastAPI" in tech_sec.content
    assert "- **Frontend & UI**:" in tech_sec.content
    assert "React.js" in tech_sec.content
    assert "- **AI & Machine Learning**:" in tech_sec.content
    assert "OpenAI gpt-5-mini" in tech_sec.content or "RapidFuzz" in tech_sec.content
    assert "- **Data, Scraping & Automation**:" in tech_sec.content
    assert "Apify" in tech_sec.content
    assert "- **DevOps & Infrastructure**:" in tech_sec.content
    assert "Git/GitHub" in tech_sec.content

    # Ensure markdown_content was regenerated with the universal bullet list
    assert "- **Backend & APIs**:" in normalized.markdown_content
    assert not "The technology stack includes" in normalized.markdown_content


@pytest.mark.asyncio
async def test_normalize_unbulleted_decisions_and_challenges():
    """Verify that dense unbulleted paragraphs in Decisions and Challenges are converted into structured bullets."""
    from app.services.case_study_generator import normalize_case_study
    from app.ai.schemas.case_study import GeneratedCaseStudy, CaseStudySection

    raw_cs = GeneratedCaseStudy(
        project_id="test_proj_2",
        title="Pipeline Architecture",
        executive_summary="Summary text.",
        sections=[
            CaseStudySection(
                title="Key Technical Decisions & Tradeoffs",
                content=(
                    "Utilizing Apify actors for scraping LinkedIn job listings and reviews. "
                    "OpenAI gpt-5-mini acts as the primary scoring engine for qualification. "
                    "FastAPI was chosen for ASGI async IO handling."
                ),
                order=1
            ),
            CaseStudySection(
                title="Engineering Challenges & Deep-dive Solutions",
                content=(
                    "Chaining multiple actors creates compounding latency across runs. "
                    "To mitigate this issue, company size pre-filtering is executed early."
                ),
                order=2
            )
        ],
        markdown_content="Initial text"
    )

    normalized = normalize_case_study(raw_cs)
    dec_sec = [s for s in normalized.sections if "decision" in s.title.lower()][0]
    chal_sec = [s for s in normalized.sections if "challenge" in s.title.lower()][0]

    assert dec_sec.format_type == "bullets"
    assert dec_sec.content.startswith("- ")

    assert chal_sec.format_type == "bullets"
    assert chal_sec.content.startswith("- ")

