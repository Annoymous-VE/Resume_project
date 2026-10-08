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
    """Verify that question generation and fallback mechanisms ask focused, conversational
    obstacle probing questions without robotic compound phrases."""
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
    # Probes for real technical hurdles/bottlenecks in a natural, focused way
    assert any(w in res.question.question.lower() for w in ["hurdle", "bottleneck", "obstacle", "challenge"])
    # Strictly ONE question — never compound
    assert res.question.question.count("?") == 1
    assert "and what specific measures did you take" not in res.question.question.lower()

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
    assert any(w in fallback_res.question.question.lower() for w in ["hurdle", "bottleneck", "obstacle", "challenge"])
    assert fallback_res.question.question.count("?") == 1

    # 3. Test clarification fallback for challenges
    clarify_res = await failing_engine.generate_clarification_response(
        project_name=knowledge.project_name,
        target_area="challenges",
        original_question=fallback_res.question.question,
        user_query="what do you mean?",
        technologies=knowledge.technologies
    )
    assert "friction" in clarify_res.question.lower() or "hurdle" in clarify_res.question.lower() or "bug" in clarify_res.question.lower()
    # Does NOT ask compound question or next question
    assert "in real-world engineering, virtually no system is built without friction" not in clarify_res.question.lower()

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


@pytest.mark.asyncio
async def test_verification_and_clarification_intent_detection():
    """Verify that InterviewEngine reliably identifies verification questions (e.g. 'Do you mean X?')
    and explanation requests, while keeping real answers as non-clarification."""
    # 1. Verification of understanding queries
    assert InterviewEngine.is_clarification_intent("Do you mean whether we used Redis or PostgreSQL?") is True
    assert InterviewEngine.is_clarification_intent("So you mean our database cache?") is True
    assert InterviewEngine.is_clarification_intent("Are you asking about the frontend or the backend API?") is True
    assert InterviewEngine.is_clarification_intent("Is this about our deployment architecture?") is True
    assert InterviewEngine.is_clarification_intent("Does this refer to database query latency?") is True
    assert InterviewEngine.is_clarification_intent("Am I understanding correctly that you want to know about our data flow?") is True
    assert InterviewEngine.is_clarification_intent("Just to clarify, should I talk about caching?") is True
    assert InterviewEngine.is_clarification_intent("Meaning how requests travel between microservices?") is True
    assert InterviewEngine.is_clarification_intent("Like whether we used Celery or RabbitMQ?") is True
    assert InterviewEngine.is_clarification_intent("what do you mean by that?") is True
    assert InterviewEngine.is_clarification_intent("Can you explain in simple terms?") is True
    assert InterviewEngine.is_clarification_intent("Could you give me an example?") is True

    # 2. Real technical answers should NOT be detected as clarification
    assert InterviewEngine.is_clarification_intent("We used Redis for caching session tokens.") is False
    assert InterviewEngine.is_clarification_intent("I built a microservices architecture using FastAPI and Docker.") is False
    assert InterviewEngine.is_clarification_intent("The biggest hurdle was thread contention under 10k concurrent requests.") is False
    assert InterviewEngine.is_clarification_intent("We chose Go because of its lightweight concurrency and goroutines.") is False
    assert InterviewEngine.is_clarification_intent("Latency was reduced from 800ms down to 45ms after indexing.") is False


@pytest.mark.asyncio
async def test_clarification_response_verifies_without_next_question():
    """Verify that clarification and verification responses directly address the user's inquiry,
    remain short/mid-sized, and NEVER introduce the next question or unrelated topics."""
    engine = InterviewEngine(llm_client=None)

    # 1. User verifying understanding: "Do you mean whether we used Redis?"
    res_verify = await engine.generate_clarification_response(
        project_name="Order Processor",
        target_area="technical_decisions",
        original_question="What made you choose this stack?",
        user_query="Do you mean whether we used Redis or PostgreSQL?",
        technologies=["Python", "Redis", "PostgreSQL"]
    )

    # Confirm it directly addresses verification
    assert res_verify.question.startswith("Yes, exactly!")
    # Stays on the same target area
    assert res_verify.target_area == "technical_decisions"
    # Does NOT ask the next question or ask a compound question
    assert "In real-world engineering" not in res_verify.question
    assert "What were the key obstacles" not in res_verify.question
    # Length is concise (less than 400 characters)
    assert len(res_verify.question) < 400

    # 2. General explanation request
    res_explain = await engine.generate_clarification_response(
        project_name="Order Processor",
        target_area="architecture",
        original_question="How does data flow end-to-end?",
        user_query="Can you explain what you mean?",
        technologies=["Python", "FastAPI"]
    )
    assert "whiteboard sketch" in res_explain.question or "building blocks" in res_explain.question
    assert res_explain.target_area == "architecture"


@pytest.mark.asyncio
async def test_single_question_conversational_probing():
    """Verify that question generation produces strictly ONE focused question per turn."""
    engine = InterviewEngine(llm_client=None)
    knowledge = ProjectKnowledge(
        project_id="test_single",
        project_name="Streaming Gateway",
        technologies=["Go", "Kafka"]
    )
    coverage = KnowledgeCoverage(
        problem=CoverageLevel.SUFFICIENT,
        architecture=CoverageLevel.SUFFICIENT,
        technical_decisions=CoverageLevel.UNKNOWN,
        challenges=CoverageLevel.UNKNOWN,
        solutions=CoverageLevel.UNKNOWN,
        tradeoffs=CoverageLevel.UNKNOWN,
        performance=CoverageLevel.UNKNOWN,
        impact=CoverageLevel.UNKNOWN
    )

    res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=2,
        latest_question="How does data flow?",
        latest_answer="Data moves from HTTP handlers into a Kafka producer with gzip compression.",
        history=[]
    )

    assert res.has_next_question is True
    # Exactly one question mark
    assert res.question.question.count("?") == 1
    # No compound questions
    assert " and what " not in res.question.question.lower()


@pytest.mark.asyncio
async def test_continue_interview_resumes_to_100_percent():
    """Verify that force_continue=True resumes an interview to gather remaining missing topics
    and terminates at 100% completion when all 8 dimensions are sufficient."""
    engine = InterviewEngine(llm_client=None)
    km = KnowledgeManager(llm_client=None)

    # 1. Setup knowledge with 7/8 dimensions SUFFICIENT and 1 missing (impact)
    knowledge = ProjectKnowledge(
        project_id="test_100_pct",
        project_name="Fintech Ledger",
        technologies=["Go", "PostgreSQL", "Kafka"],
        technical_decisions=["Chose PostgreSQL for ACID compliance in financial balances"],
        challenges=["Deadlock under high volume concurrent debit transactions"],
        solutions=["Introduced account-level advisory locks before balance updates"],
        tradeoffs=["Serializing accounts lowers concurrency for shared accounts"],
        performance=["Processed 12,000 tx/sec with p99 latency under 25ms"],
        impact=[]  # Missing impact
    )
    knowledge.problem.statement = "Financial transactions experienced balance inconsistencies."
    knowledge.problem.context = "During flash sale events thousands of concurrent debits caused race conditions."
    knowledge.architecture.overview = "Microservice architecture using Go and PostgreSQL."
    knowledge.architecture.components = ["Ledger API", "Event Stream", "Audit Store"]

    coverage = km.compute_coverage(knowledge)
    cov_dict = coverage.model_dump()
    assert cov_dict["impact"] == CoverageLevel.UNKNOWN
    assert sum(1 for v in cov_dict.values() if v == CoverageLevel.SUFFICIENT.value) == 7

    # 2. Standard call at round 6 stops early due to high completeness (7/8)
    standard_res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=6,
        latest_question="What performance metrics did you measure?",
        latest_answer="12k tx/sec with 25ms latency",
        history=[],
        force_continue=False
    )
    assert standard_res.has_next_question is False

    # 3. Continued call with force_continue=True OVERRIDES early stop and targets missing dimension (impact)
    continue_res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=coverage,
        current_round=6,
        latest_question="What performance metrics did you measure?",
        latest_answer="12k tx/sec with 25ms latency",
        history=[],
        force_continue=True
    )
    assert continue_res.has_next_question is True
    assert continue_res.question.target_area == "impact"

    # 4. Answer the missing impact question
    knowledge = km.merge_answer(
        current_knowledge=knowledge,
        target_area="impact",
        answer_text="Eliminated 100% of ledger reconciliation errors and prevented over $2M in financial leakage.",
        exchange_id="ex_impact"
    )

    # 5. Recompute coverage: Now 8/8 dimensions SUFFICIENT (100% complete)
    updated_coverage = km.compute_coverage(knowledge)
    updated_cov_dict = updated_coverage.model_dump()
    assert updated_cov_dict["impact"] == CoverageLevel.SUFFICIENT
    assert sum(1 for v in updated_cov_dict.values() if v == CoverageLevel.SUFFICIENT.value) == 8

    # 6. Now select_next_question returns has_next_question=False and declares 100% completion
    final_res = await engine.select_next_question(
        knowledge=knowledge,
        coverage=updated_coverage,
        current_round=7,
        latest_question=continue_res.question.question,
        latest_answer="Eliminated 100% of ledger reconciliation errors and prevented $2M leakage.",
        history=[],
        force_continue=True
    )
    assert final_res.has_next_question is False
    assert "100%" in final_res.stop_reason







