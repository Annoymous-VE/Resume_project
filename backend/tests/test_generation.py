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


@pytest.mark.asyncio
async def test_client_brochure_schema_and_prompt_structure():
    """Verify Client Brochure schema validation and prompt adherence to business value rules."""
    from app.ai.schemas.case_study import GeneratedClientBrochure, ClientBrochureMetric, CaseStudySection
    from app.ai.prompts.case_study import CLIENT_BROCHURE_SYSTEM_PROMPT, CLIENT_BROCHURE_USER_PROMPT

    # 1. Verify schema construction and validation
    brochure = GeneratedClientBrochure(
        project_id="client_proj_1",
        title="Automated Multi-Channel Prospecting Engine",
        tagline="Empowering sales teams to scale outreach by 5x with zero manual research.",
        executive_summary="Designed to streamline lead qualification and automate repetitive data enrichment pipelines.",
        target_audience="B2B Enterprise Sales & Revenue Operations Teams",
        key_metrics=[
            ClientBrochureMetric(label="Lead Velocity", value="5x Increase", description="Automated discovery and qualification speed"),
            ClientBrochureMetric(label="Cost Savings", value="60% Reduction", description="Decreased third-party data enrichment spend")
        ],
        sections=[
            CaseStudySection(
                title="Executive Summary & Value Proposition",
                format_type="paragraph",
                content="A cohesive executive overview highlighting strategic growth.",
                order=1
            ),
            CaseStudySection(
                title="The Business Challenge & Client Pain Points",
                format_type="hybrid",
                content="Manual prospecting was bottlenecking sales efficiency.\n- **Wasted Time**: Reps spent 15 hours/week on data entry.",
                order=2
            )
        ],
        markdown_content="# Automated Multi-Channel Prospecting Engine\n\n*Empowering sales teams to scale outreach by 5x.*"
    )

    assert brochure.project_id == "client_proj_1"
    assert len(brochure.key_metrics) == 2
    assert brochure.key_metrics[0].value == "5x Increase"
    assert brochure.sections[0].format_type == "paragraph"

    # 2. Verify prompt guidelines enforce business focus and omitting low-level code
    assert "business value" in CLIENT_BROCHURE_SYSTEM_PROMPT.lower()
    assert "omit low-level code" in CLIENT_BROCHURE_SYSTEM_PROMPT.lower()
    assert "roi" in CLIENT_BROCHURE_SYSTEM_PROMPT.lower()
    assert "delivered capabilities" in CLIENT_BROCHURE_SYSTEM_PROMPT.lower() or "delivered solution" in CLIENT_BROCHURE_SYSTEM_PROMPT.lower()

    # 3. Verify user prompt placeholder formatting
    formatted_user_prompt = CLIENT_BROCHURE_USER_PROMPT.format(project_knowledge_json='{"project": "Test"}')
    assert '{"project": "Test"}' in formatted_user_prompt
    assert "Executive Summary & Value Proposition" in formatted_user_prompt


@pytest.mark.asyncio
async def test_mock_llm_client_brochure_generation():
    """Verify that MockLLMClient successfully returns a valid GeneratedClientBrochure."""
    from app.ai.llm import MockLLMClient
    from app.ai.schemas.case_study import GeneratedClientBrochure
    from app.ai.prompts.case_study import CLIENT_BROCHURE_SYSTEM_PROMPT, CLIENT_BROCHURE_USER_PROMPT

    llm = MockLLMClient()
    result = await llm.generate_structured(
        prompt=CLIENT_BROCHURE_USER_PROMPT.format(project_knowledge_json="{}"),
        schema=GeneratedClientBrochure,
        system_prompt=CLIENT_BROCHURE_SYSTEM_PROMPT
    )

    assert isinstance(result, GeneratedClientBrochure)
    assert result.project_id == "proj_brochure"
    assert len(result.key_metrics) >= 1
    assert len(result.sections) >= 3
    assert "Enterprise" in result.title
    assert result.sections[0].format_type == "paragraph"


@pytest.mark.asyncio
async def test_multi_variant_case_study_models():
    """Verify that Project supports multiple CaseStudyRecord variants (one-to-many relationship)."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.models.base import Base
    from app.models.entities import Project, CaseStudyRecord
    from app.repositories.case_study_repository import CaseStudyRepository

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create a project
        project = Project(
            id="proj_multi_test",
            name="Cloud Optimization Engine",
            description="Multi-cloud resource orchestrator",
            data_json={"tech": ["Python", "AWS"]}
        )
        session.add(project)
        await session.flush()

        repo = CaseStudyRepository(session)

        # 1. Save technical case study
        tech_study = await repo.save_case_study(
            project_id=project.id,
            title="Cloud Optimization Engine - Technical Analysis",
            markdown_content="# Technical Analysis\nDetailed architecture.",
            sections_json=[{"title": "Architecture", "content": "Microservices"}],
            variant_type="technical"
        )
        assert tech_study.variant_type == "technical"

        # 2. Save client brochure case study for the same project
        brochure_study = await repo.save_case_study(
            project_id=project.id,
            title="Cloud Optimization Engine - Client Overview",
            markdown_content="# Client Overview\n35% Cloud Spend Reduction.",
            sections_json=[{"title": "Value Proposition", "content": "Cost savings"}],
            variant_type="client_brochure"
        )
        assert brochure_study.variant_type == "client_brochure"

        # 3. Verify retrieving by variant_type
        retrieved_tech = await repo.get_case_study(project.id, variant_type="technical")
        assert retrieved_tech is not None
        assert retrieved_tech.title == "Cloud Optimization Engine - Technical Analysis"

        retrieved_brochure = await repo.get_case_study(project.id, variant_type="client_brochure")
        assert retrieved_brochure is not None
        assert retrieved_brochure.title == "Cloud Optimization Engine - Client Overview"

        # 4. Verify get_all_case_studies
        all_studies = await repo.get_all_case_studies(project.id)
        assert len(all_studies) == 2
        variants = {s.variant_type for s in all_studies}
        assert variants == {"technical", "client_brochure"}

        # 5. Verify Project relationship and backwards-compatible .case_study property
        proj_res = await session.execute(
            select(Project).where(Project.id == project.id)
        )
        loaded_proj = proj_res.scalars().first()
        assert len(loaded_proj.case_studies) == 2
        assert loaded_proj.case_study.variant_type == "technical"


def test_export_brochure_to_pdf_and_docx():
    """Verify that CaseStudyExporter produces valid PDF and Word documents for client brochures."""
    from app.services.case_study_exporter import CaseStudyExporter

    brochure_md = (
        "# Enterprise Distributed Cache & Performance Acceleration Suite\n\n"
        "*Accelerating enterprise data throughput by 10x with zero downtime.*\n\n"
        "## Executive Summary & Value Proposition\n"
        "Engineered to tackle critical latency constraints and deliver continuous operational resilience.\n\n"
        "## The Business Challenge & Client Pain Points\n"
        "Operational bottlenecks were impeding response times and increasing infrastructure overhead.\n"
        "- **Bottleneck Risk**: High database lock contention during traffic spikes.\n"
        "- **Scalability Constraint**: Legacy systems could not scale linearly.\n\n"
        "## Delivered Solution & Core Capabilities\n"
        "A unified acceleration layer providing seamless throughput.\n"
        "- **Real-Time Data Ingestion**: Non-blocking connection management.\n"
        "- **Operational Resilience**: Zero downtime failover protection.\n\n"
        "## Business Impact & Measured ROI\n"
        "- **Operational Throughput**: **100k requests/second** — sustained with sub-millisecond overhead.\n"
        "- **Hardware Efficiency**: **45% reduction** — in required backend compute instances.\n"
    )

    # 1. Test brochure PDF export directly
    pdf_buffer = CaseStudyExporter.export_brochure_to_pdf(
        title="Enterprise Distributed Cache",
        markdown_content=brochure_md
    )
    assert pdf_buffer is not None
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # 2. Test export_to_pdf with variant_type="client_brochure"
    pdf_variant_buffer = CaseStudyExporter.export_to_pdf(
        title="Enterprise Distributed Cache",
        markdown_content=brochure_md,
        variant_type="client_brochure"
    )
    assert pdf_variant_buffer is not None
    assert pdf_variant_buffer.getvalue().startswith(b"%PDF")

    # 3. Test brochure DOCX export
    docx_buffer = CaseStudyExporter.export_to_docx(
        title="Enterprise Distributed Cache",
        markdown_content=brochure_md,
        variant_type="client_brochure"
    )
    assert docx_buffer is not None
    docx_bytes = docx_buffer.getvalue()
    assert len(docx_bytes) > 1000
    assert docx_bytes.startswith(b"PK")




