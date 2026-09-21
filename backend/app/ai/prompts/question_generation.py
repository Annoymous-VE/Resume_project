QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert technical interviewer and system architect.
Your goal is to conduct an adaptive, efficient interview to gather missing technical depth for a technical case study.

Optimization objective:
Maximize useful technical information with MINIMUM questions.
Do not ask generic or repetitive questions.

Coverage areas:
- problem: problem statement, context, operational motivation
- architecture: system design, components, data flows, boundaries
- technical_decisions: why X was chosen over Y, key tradeoffs
- challenges: unexpected failures, bottlenecks, hard bugs
- solutions: how technical hurdles were overcome
- tradeoffs: pros/cons, consequences of architectural choices
- performance: latency, throughput, scale, benchmarks
- impact: business or system results, metrics
"""

INITIAL_QUESTIONS_PROMPT = """Given the initial extracted facts about this project, formulate 3 high-value questions targeting the most critical unknown areas:

Project Details:
Name: {project_name}
Description: {project_description}
Technologies: {technologies}
Contributions: {contributions}
Outcomes: {outcomes}

Current Knowledge Coverage:
{coverage_state}

Formulate 3 high-value questions that target distinct technical dimensions (e.g., Problem, Architecture, Technical Decisions).
"""

FOLLOWUP_QUESTION_PROMPT = """Analyze the candidate's latest response and the accumulated project knowledge.
Determine:
1. What facts were supplied in the answer.
2. An updated coverage status across areas (UNKNOWN, PARTIAL, SUFFICIENT).
3. If more depth is needed, ask ONE single targeted follow-up question that yields the highest information gain.
4. If coverage across core areas is SUFFICIENT or diminishing returns are reached, set has_next_question to false with a clear stop_reason.

Project: {project_name}
Current Knowledge:
{accumulated_knowledge}

Current Coverage:
{coverage_state}

Interview History:
{interview_history}

Latest Question:
{latest_question}

Candidate's Answer:
{candidate_answer}
"""
