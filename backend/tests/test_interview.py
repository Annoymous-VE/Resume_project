import pytest
from app.ai.llm import MockLLMClient
from app.services.knowledge_manager import KnowledgeManager
from app.services.interview_engine import InterviewEngine
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import CoverageLevel

@pytest.mark.asyncio
async def test_adaptive_interview_lifecycle():
    llm = MockLLMClient()
    km = KnowledgeManager()
    engine = InterviewEngine(llm)

    project = ExtractedProject(
        id="p1",
        name="Telemetry Pipeline",
        description="Streaming telemetry processing",
        technologies=["Go", "Kafka"],
        contributions=["Built consumer cluster"],
        outcomes=["Processed 10k eps"]
    )

    # 1. Initialize knowledge
    knowledge = km.initialize_knowledge(project)
    assert knowledge.project_name == "Telemetry Pipeline"
    assert len(knowledge.evidence) > 0

    # 2. Compute initial coverage
    cov = km.compute_coverage(knowledge)
    assert cov.problem != CoverageLevel.UNKNOWN

    # 3. Initial questions
    questions = await engine.generate_initial_questions(project, cov)
    assert len(questions) >= 1
    assert questions[0].target_area in ["problem", "architecture", "technical_decisions"]

    # 4. Answer question and update knowledge
    knowledge = km.merge_answer(
        current_knowledge=knowledge,
        target_area="architecture",
        answer_text="Designed with a partitioned Kafka topic and consumer workers with local RocksDB cache.",
        exchange_id="ex_1"
    )
    assert len(knowledge.architecture.components) > 0

    # 5. Check stopping condition
    stop_res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=cov,
        current_round=10, # Exceeds MAX_INTERVIEW_ROUNDS
        latest_question="Sample Q",
        latest_answer="Sample A",
        history=[]
    )
    assert stop_res.has_next_question is False
    assert "Maximum configured interview rounds" in (stop_res.stop_reason or "")

@pytest.mark.asyncio
async def test_multi_criteria_extraction():
    llm = MockLLMClient()
    km = KnowledgeManager(llm_client=llm)

    project = ExtractedProject(
        id="p2",
        name="Lead Engine",
        description="Lead extraction and scoring",
        technologies=["Python", "FastAPI"]
    )
    knowledge = km.initialize_knowledge(project)

    # User answer mentioning both architecture and performance
    rich_answer = "We used an asynchronous Celery queue with Redis to decouple API scraping, which cut latency down to 250ms."
    updated_knowledge = await km.extract_and_merge_answer(
        current_knowledge=knowledge,
        target_area="architecture",
        answer_text=rich_answer,
        exchange_id="ex_test"
    )

    # Verify facts were categorized
    evidence_cats = [e.category for e in updated_knowledge.evidence if e.source == "conversation"]
    assert len(evidence_cats) >= 1
    cov = km.compute_coverage(updated_knowledge)
    assert cov.architecture != CoverageLevel.UNKNOWN

