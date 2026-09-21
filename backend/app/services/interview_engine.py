import json
from typing import List, Optional, Dict
from app.ai.llm import BaseLLMClient
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import (
    ProjectKnowledge,
    KnowledgeCoverage,
    CoverageLevel
)
from app.ai.schemas.question import (
    GeneratedQuestion,
    InitialQuestionsResult,
    FollowUpQuestionResult
)
from app.ai.prompts.question_generation import (
    QUESTION_GENERATION_SYSTEM_PROMPT,
    INITIAL_QUESTIONS_PROMPT,
    FOLLOWUP_QUESTION_PROMPT
)
from app.config import settings

class InterviewEngine:
    """
    Adaptive Interview Engine.
    Optimizes for maximum information gain with minimum questions.
    Selects one targeted follow-up question based on coverage gaps.
    Enforces clear stopping conditions.
    """

    AREA_PRIORITIES = [
        "problem",
        "architecture",
        "technical_decisions",
        "challenges",
        "performance",
        "tradeoffs",
        "impact"
    ]

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def generate_initial_questions(
        self,
        project: ExtractedProject,
        coverage: KnowledgeCoverage
    ) -> List[GeneratedQuestion]:
        """Generate initial high-value questions covering primary unknowns."""
        prompt = INITIAL_QUESTIONS_PROMPT.format(
            project_name=project.name,
            project_description=project.description or "N/A",
            technologies=", ".join(project.technologies) if project.technologies else "N/A",
            contributions="; ".join(project.contributions) if project.contributions else "N/A",
            outcomes="; ".join(project.outcomes) if project.outcomes else "N/A",
            coverage_state=json.dumps(coverage.model_dump(), indent=2)
        )

        try:
            res = await self.llm.generate_structured(
                prompt=prompt,
                schema=InitialQuestionsResult,
                system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT
            )
            if res.questions:
                return res.questions[:3]
        except Exception:
            pass

        # Deterministic fallback questions
        return [
            GeneratedQuestion(
                id="q_prob_1",
                target_area="problem",
                question=f"What core operational or engineering challenge did {project.name} solve, and why was it necessary?",
                rationale="Uncovers problem statement, business motivation, and operational constraints."
            ),
            GeneratedQuestion(
                id="q_arch_1",
                target_area="architecture",
                question=f"How did you design the architecture for {project.name}, and what were the primary data flows between components?",
                rationale="Extracts system topology, message patterns, and component responsibilities."
            ),
            GeneratedQuestion(
                id="q_dec_1",
                target_area="technical_decisions",
                question=f"What key tradeoffs or technical considerations drove your decision to use {', '.join(project.technologies[:2]) if project.technologies else 'your stack'}?",
                rationale="Identifies decision-making criteria and engineering tradeoffs."
            )
        ]

    async def select_next_question(
        self,
        knowledge: ProjectKnowledge,
        coverage: KnowledgeCoverage,
        current_round: int,
        latest_question: str,
        latest_answer: str,
        history: List[Dict[str, str]]
    ) -> FollowUpQuestionResult:
        """Analyze answer and select ONE high-value follow-up or stop."""
        
        # Check stopping conditions first
        # 1. Max interview rounds reached
        if current_round >= settings.MAX_INTERVIEW_ROUNDS:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="Maximum configured interview rounds reached.",
                coverage_update={}
            )

        # 2. Check if primary core areas are already SUFFICIENT
        cov_dict = coverage.model_dump()
        core_areas = ["problem", "architecture", "technical_decisions", "challenges"]
        sufficient_count = sum(1 for a in core_areas if cov_dict.get(a) == CoverageLevel.SUFFICIENT.value)

        if sufficient_count >= 3 and current_round >= 3:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="Sufficient coverage across core architectural dimensions achieved.",
                coverage_update={}
            )

        # Find highest priority area with UNKNOWN or PARTIAL coverage
        target_area = None
        for area in self.AREA_PRIORITIES:
            val = cov_dict.get(area)
            if val in (CoverageLevel.UNKNOWN.value, CoverageLevel.PARTIAL.value):
                target_area = area
                break

        if not target_area:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="All technical dimensions sufficiently covered for case study.",
                coverage_update={}
            )

        # Prompt LLM for targeted follow-up
        history_text = "\n".join([
            f"Q: {h.get('question')}\nA: {h.get('answer')}"
            for h in history
        ])

        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            project_name=knowledge.project_name,
            accumulated_knowledge=json.dumps(knowledge.model_dump(exclude={"evidence"}), indent=2),
            coverage_state=json.dumps(cov_dict, indent=2),
            interview_history=history_text or "None",
            latest_question=latest_question,
            candidate_answer=latest_answer
        )

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                schema=FollowUpQuestionResult,
                system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT
            )
            if result.has_next_question and result.question:
                return result
        except Exception:
            pass

        # Fallback question for target area
        fallback_questions = {
            "problem": f"What was the scale or context of the problem before {knowledge.project_name} was introduced?",
            "architecture": f"Could you specify how data consistency, state, or concurrency was handled across components?",
            "technical_decisions": f"What alternatives did you evaluate before settling on your chosen architectural design?",
            "challenges": f"What was the single hardest engineering bug, bottleneck, or system failure you resolved in this project?",
            "performance": f"What specific latency, throughput, or resource utilization metrics did the system achieve?",
            "tradeoffs": f"What downsides, operational overhead, or limitations did this design introduce?",
            "impact": f"What concrete measurable outcome or efficiency gain did this deliver for users or the engineering team?"
        }

        q_text = fallback_questions.get(
            target_area,
            f"Could you elaborate on the technical implementation and outcomes of {knowledge.project_name}?"
        )

        return FollowUpQuestionResult(
            has_next_question=True,
            question=GeneratedQuestion(
                id=f"q_{target_area}_{current_round + 1}",
                target_area=target_area,
                question=q_text,
                rationale=f"Fills critical missing details in {target_area}."
            ),
            coverage_update={target_area: CoverageLevel.PARTIAL}
        )
