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
