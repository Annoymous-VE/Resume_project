import pytest
from app.ai.llm import MockLLMClient
from app.services.knowledge_manager import KnowledgeManager
from app.services.interview_engine import InterviewEngine
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import CoverageLevel, ProjectKnowledge, KnowledgeCoverage

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

@pytest.mark.asyncio
async def test_mandatory_obstacle_phase_gate():
    """Verify that interview cannot finish or terminate early until at least one concrete
    obstacle and its corresponding mitigation have been gathered."""
    llm = MockLLMClient()
    engine = InterviewEngine(llm)

    # 1. Create knowledge with high completeness on other dimensions (6 dimensions sufficient)
    # BUT zero challenges and zero solutions recorded
    knowledge = ProjectKnowledge(
        project_id="gate_test",
        project_name="High-Frequency Gateway",
        technical_decisions=["Chose C++ for zero-cost abstractions"],
        tradeoffs=["Increased development cycle time for memory safety"],
        performance=["Processed 1M ops/sec at 12us p99"],
        impact=["Zero downtime throughout peak traffic"],
        technologies=["C++", "Boost.Asio"]
    )
    knowledge.architecture.components = ["Ingestion Gateway", "Matching Engine"]
    knowledge.problem.statement = "Order placement bottleneck under burst traffic."

    from app.ai.schemas.knowledge import KnowledgeCoverage, CoverageLevel
    coverage = KnowledgeCoverage(
        problem=CoverageLevel.SUFFICIENT,
        architecture=CoverageLevel.SUFFICIENT,
        technical_decisions=CoverageLevel.SUFFICIENT,
        challenges=CoverageLevel.UNKNOWN,
        solutions=CoverageLevel.UNKNOWN,
        tradeoffs=CoverageLevel.SUFFICIENT,
        performance=CoverageLevel.SUFFICIENT,
        impact=CoverageLevel.SUFFICIENT
    )

    # Round 5 with 6/8 dimensions SUFFICIENT:
    # Normally would be eligible for completion, but obstacle gate MUST BLOCK IT
    res1 = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=5,
        latest_question="What about impact?",
        latest_answer="Zero downtime observed.",
        history=[]
    )
    assert res1.has_next_question is True
    assert res1.question.target_area == "challenges"

    # 2. Simulate candidate answering with an obstacle, but NO mitigation yet
    knowledge.challenges.append("Thread contention on shared memory ring buffer caused 10x latency spikes.")
    coverage.challenges = CoverageLevel.SUFFICIENT

    # Obstacle gathered, but mitigation missing: phase-gate MUST STILL BLOCK completion and target solutions
    res2 = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=6,
        latest_question="What obstacle did you encounter?",
        latest_answer="Contention on memory buffer.",
        history=[]
    )
    assert res2.has_next_question is True
    assert res2.question.target_area == "solutions"

    # 3. Simulate candidate answering with the mitigation
    knowledge.solutions.append("Refactored to single-producer single-consumer lock-free SPSC ring buffers.")
    coverage.solutions = CoverageLevel.SUFFICIENT

    # Now BOTH obstacle and mitigation are gathered (8/8 dimensions sufficient):
    # Phase-gate allows completion!
    res3 = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=7,
        latest_question="How did you resolve it?",
        latest_answer="Implemented lock-free ring buffers.",
        history=[]
    )
    assert res3.has_next_question is False
    assert "sufficiently covered" in (res3.stop_reason or "").lower()

@pytest.mark.asyncio
async def test_targeted_probing_prompt_for_obstacles():
    """Verify that question generation and fallback mechanisms explicitly ask the targeted
    real-world engineering friction and obstacle probing question."""
    llm = MockLLMClient()
    engine = InterviewEngine(llm)

    knowledge = ProjectKnowledge(
        project_id="probe_test",
        project_name="Data Ingestion Bus",
        technologies=["Python", "Kafka", "PostgreSQL"]
    )
    coverage = KnowledgeCoverage(
        problem=CoverageLevel.SUFFICIENT,
        architecture=CoverageLevel.SUFFICIENT,
        technical_decisions=CoverageLevel.SUFFICIENT,
        challenges=CoverageLevel.UNKNOWN,
        solutions=CoverageLevel.UNKNOWN,
        tradeoffs=CoverageLevel.UNKNOWN,
        performance=CoverageLevel.UNKNOWN,
        impact=CoverageLevel.UNKNOWN
    )

    # 1. Test LLM-generated probing question when targeting challenges
    res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=3,
        latest_question="What about your decisions?",
        latest_answer="We chose Kafka for high throughput.",
        history=[]
    )
    assert res.has_next_question is True
    assert res.question.target_area == "challenges"
    expected_probing_text = (
        "In real-world engineering, virtually no system is built without friction. "
        "What were the key obstacles, architectural bottlenecks, or failure modes you encountered, "
        "and what specific measures did you take to overcome them?"
    )
    assert expected_probing_text in res.question.question

    # 2. Test fallback question when LLM is unavailable or fails
    failing_engine = InterviewEngine(llm_client=None)
    fallback_res = await failing_engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=3,
        latest_question="What about your decisions?",
        latest_answer="We chose Kafka for high throughput.",
        history=[]
    )
    assert fallback_res.has_next_question is True
    assert fallback_res.question.target_area == "challenges"
    assert "In real-world engineering, virtually no system is built without friction." in fallback_res.question.question
    assert "What were the key obstacles, architectural bottlenecks, or failure modes you encountered" in fallback_res.question.question

    # 3. Test clarification fallback for challenges
    clarify_res = await failing_engine.generate_clarification_response(
        project_name=knowledge.project_name,
        target_area="challenges",
        original_question=fallback_res.question.question,
        user_query="what do you mean?",
        technologies=knowledge.technologies
    )
    assert "In real-world engineering, virtually no system is built without friction." in clarify_res.question

@pytest.mark.asyncio
async def test_fallback_escalation_for_superficial_answers():
    """Verify detection of dismissive/superficial replies and automatic escalation with category prompts."""
    llm = MockLLMClient()
    engine = InterviewEngine(llm)

    # 1. Test detection of dismissive replies
    assert engine.is_dismissive_reply("everything went smoothly") is True
    assert engine.is_dismissive_reply("Everything went smoothly.") is True
    assert engine.is_dismissive_reply("there were no issues") is True
    assert engine.is_dismissive_reply("we faced no challenges") is True
    assert engine.is_dismissive_reply("nothing went wrong") is True
    assert engine.is_dismissive_reply("smooth sailing") is True
    assert engine.is_dismissive_reply("none") is True
    assert engine.is_dismissive_reply("We had a race condition in our distributed cache during failover.") is False

    # 2. Test that dismissive replies do not pass the obstacle gate
    knowledge = ProjectKnowledge(
        project_id="superficial_test",
        project_name="Order Processor",
        challenges=["everything went smoothly"],
        technologies=["Python", "PostgreSQL"]
    )
    assert engine.has_concrete_obstacle(knowledge) is False

    # 3. Test automatic category escalation question generation
    coverage = KnowledgeCoverage(
        problem=CoverageLevel.SUFFICIENT,
        architecture=CoverageLevel.SUFFICIENT,
        technical_decisions=CoverageLevel.SUFFICIENT,
        challenges=CoverageLevel.UNKNOWN,
        solutions=CoverageLevel.UNKNOWN,
        tradeoffs=CoverageLevel.UNKNOWN,
        performance=CoverageLevel.UNKNOWN,
        impact=CoverageLevel.UNKNOWN
    )

    res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=4,
        latest_question="What were the key obstacles or failure modes?",
        latest_answer="everything went smoothly",
        history=[]
    )

    assert res.has_next_question is True
    assert res.question.target_area == "challenges"
    expected_escalation = (
        "Even well-designed architectures face constraints like API rate limits, "
        "database locks, slow queries, or third-party integration bugs. Which of these did you experience?"
    )
    assert expected_escalation in res.question.question

@pytest.mark.asyncio
async def test_structured_obstacle_mitigation_pairs_extraction():
    """Verify that knowledge extraction pass stores challenges as structured pairs:
    Obstacle, Root Cause, Measures Taken, Outcome."""
    llm = MockLLMClient()
    km = KnowledgeManager(llm_client=llm)
    engine = InterviewEngine(llm)

    project = ExtractedProject(
        id="p_obstacle",
        name="High-Throughput Exchange",
        technologies=["Go", "Kafka", "PostgreSQL"]
    )
    knowledge = km.initialize_knowledge(project)

    # 1. Answer with a rich obstacle and mitigation description
    rich_answer = (
        "We hit database deadlock bottlenecks and thread contention when concurrent checkout requests exceeded 5,000 req/sec. "
        "We resolved it by refactoring to single-producer single-consumer lock-free ring buffers and batching writes with Redis caching, "
        "which eliminated all deadlocks and reduced p99 latency to 18ms."
    )

    updated_knowledge = await km.extract_and_merge_answer(
        current_knowledge=knowledge,
        target_area="challenges",
        answer_text=rich_answer,
        exchange_id="ex_obs_1"
    )

    # 2. Verify structured pair exists and has all 4 required dimensions
    assert len(updated_knowledge.obstacle_mitigations) >= 1
    pair = updated_knowledge.obstacle_mitigations[0]
    assert pair.obstacle is not None and len(pair.obstacle) > 10
    assert pair.root_cause is not None and len(pair.root_cause) > 5
    assert pair.measures_taken is not None and len(pair.measures_taken) > 5
    assert pair.outcome is not None and len(pair.outcome) > 5

    # 3. Verify backward compatibility with challenges and solutions lists
    assert pair.obstacle in updated_knowledge.challenges
    assert pair.measures_taken in updated_knowledge.solutions

    # 4. Verify phase-gate recognizes the structured pair
    assert engine.has_concrete_obstacle(updated_knowledge) is True
    assert engine.has_concrete_mitigation(updated_knowledge) is True
    assert engine.has_obstacle_and_mitigation(updated_knowledge) is True

    # 5. Verify coverage reflects sufficient coverage for both
    cov = km.compute_coverage(updated_knowledge)
    assert cov.challenges == CoverageLevel.SUFFICIENT
    assert cov.solutions == CoverageLevel.SUFFICIENT

    # 6. Verify fallback direct merge without LLM handles structured pairs
    km_no_llm = KnowledgeManager(llm_client=None)
    fallback_knowledge = km_no_llm.initialize_knowledge(project)
    
    # Merge challenge
    fallback_knowledge = km_no_llm.merge_answer(
        current_knowledge=fallback_knowledge,
        target_area="challenges",
        answer_text="Rate limit spikes from third-party payment API caused connection timeouts.",
        exchange_id="ex_fallback_1"
    )
    assert len(fallback_knowledge.obstacle_mitigations) >= 1
    assert "Rate limit spikes" in fallback_knowledge.obstacle_mitigations[-1].obstacle

    # Merge solution
    fallback_knowledge = km_no_llm.merge_answer(
        current_knowledge=fallback_knowledge,
        target_area="solutions",
        answer_text="Implemented exponential backoff with jitter and Redis caching.",
        exchange_id="ex_fallback_2"
    )
    assert fallback_knowledge.obstacle_mitigations[-1].measures_taken == "Implemented exponential backoff with jitter and Redis caching."





