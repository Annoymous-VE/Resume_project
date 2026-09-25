import json
import re
import uuid
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
    FOLLOWUP_QUESTION_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
    CLARIFICATION_PROMPT
)
from app.config import settings

class InterviewEngine:
    """
    Adaptive Interview Engine.
    Optimizes for maximum information gain with minimum questions.
    Selects one targeted follow-up question based on coverage gaps.
    Enforces clear stopping conditions.
    Provides friendly explanations and assistance when developers need clarification.
    """

    AREA_PRIORITIES = [
        # Core dimensions: prioritized first to establish foundation
        "problem",
        "architecture",
        "technical_decisions",
        "challenges",
        # In-depth dimensions: queried next to maximize technical depth
        "solutions",
        "tradeoffs",
        "performance",
        "impact"
    ]

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    @staticmethod
    def is_clarification_intent(text: str) -> bool:
        """Detect whether the user is asking for clarification, explanation, or expressing confusion."""
        if not text:
            return False
        clean = text.strip().lower()

        clarification_patterns = [
            r"what do you mean",
            r"what does .* mean",
            r"what do you want to know",
            r"what are you asking",
            r"what is meant by",
            r"can you explain",
            r"could you explain",
            r"please explain",
            r"explain this",
            r"explain it",
            r"explain in simple",
            r"don'?t understand",
            r"do not understand",
            r"didn'?t understand",
            r"did not understand",
            r"not clear",
            r"i'?m confused",
            r"im confused",
            r"give me an example",
            r"can you give .* example",
            r"could you give .* example",
            r"such as\?",
            r"like what\?",
            r"what part",
            r"which part",
            r"how should i answer",
            r"what should i say",
            r"what should i answer",
            r"how to answer",
            r"can you rephrase",
            r"could you rephrase",
            r"simplify",
            r"in simple words",
            r"in plain terms",
            r"help me",
            r"what are alternatives",
            r"what is alternative",
            r"why do you ask",
            r"huh\?",
            r"pardon\?",
        ]
        for pattern in clarification_patterns:
            if re.search(pattern, clean):
                return True

        # If it's a short question ending in ? and has inquiry words
        if clean.endswith("?") and len(clean.split()) <= 12:
            if any(w in clean for w in ["what", "why", "how", "which", "who", "can you", "could you", "mean"]):
                return True

        return False

    @staticmethod
    def is_skip_intent(text: str) -> bool:
        """Detect whether the user explicitly wants to pass/skip this question."""
        if not text:
            return False
        clean = text.strip().lower().rstrip(".!?,")
        skip_phrases = {
            "skip", "skip this", "skip this question", "skip question",
            "pass", "next question", "move on", "next please",
            "i don't know", "i dont know", "don't know", "dont know",
            "no idea", "not sure", "n/a", "na", "not applicable"
        }
        return clean in skip_phrases or clean.startswith("skip") or clean.startswith("let's skip")

    async def generate_clarification_response(
        self,
        project_name: str,
        target_area: str,
        original_question: str,
        user_query: str,
        technologies: Optional[List[str]] = None
    ) -> GeneratedQuestion:
        """Generate a simple, friendly explanation and concrete assistance for the current question."""
        tech_list = technologies or []
        tech_str = ", ".join(tech_list[:3]) if tech_list else "your tech stack"

        # Prompt LLM if available
        if self.llm:
            try:
                prompt = CLARIFICATION_PROMPT.format(
                    project_name=project_name,
                    original_question=original_question,
                    target_area=target_area,
                    technologies=tech_str,
                    user_query=user_query
                )
                text = await self.llm.generate_text(
                    prompt=prompt,
                    system_prompt=CLARIFICATION_SYSTEM_PROMPT
                )
                clean_text = text.strip()
                if clean_text and len(clean_text) > 15:
                    return GeneratedQuestion(
                        id=f"clarify_{target_area}_{uuid.uuid4().hex[:6]}",
                        target_area=target_area,
                        question=clean_text,
                        rationale=f"Explaining {target_area} in simple terms to help you answer."
                    )
            except Exception:
                pass

        # Rich, friendly fallback clarifications tailored to the target area & stack
        fallback_clarifications = {
            "technical_decisions": (
                f"No worries at all! In simple words: out of all the tools and frameworks out there, "
                f"what made you decide to use {tech_str}? For example, did you choose it for reliability, "
                f"built-in features, team familiarity, or because it solved a specific need? "
                f"Even a brief reason works great, or let me know what part feels unclear!"
            ),
            "problem": (
                f"Happy to explain! In plain terms: what real-world headache or manual hassle "
                f"was {project_name} built to solve? Who was experiencing the problem, and why couldn't "
                f"existing tools do the job? Feel free to share in your own everyday words!"
            ),
            "architecture": (
                f"No problem! What I mean is: if you had to draw a simple whiteboard sketch of {project_name}, "
                f"what are the main building blocks and how do they talk to each other? "
                f"(For example: User -> Web UI -> Backend -> Database). A quick high-level summary is plenty!"
            ),
            "challenges": (
                f"All good! Basically, while developing {project_name}, what was the trickiest bug, "
                f"performance bottleneck, tricky integration, or unexpected hurdle you had to solve? "
                f"For instance, did you run into rate limits, data sync bugs, or slow queries? Any hurdle counts!"
            ),
            "solutions": (
                f"Happy to clarify! How did you end up fixing or working around that technical hurdle? "
                f"For example, did you rewrite a query, add caching, switch a library, or adjust system configuration?"
            ),
            "tradeoffs": (
                f"No worries! In engineering, every technical choice has pros and cons. "
                f"What was a compromise or downside with this design? (For example: was it slightly slower to develop, "
                f"more complex to maintain, or took more memory?)"
            ),
            "performance": (
                f"Happy to explain! Did you track or notice any speed, throughput, or capacity numbers? "
                f"Even rough ballpark estimates (like 'handled ~100 requests/sec' or 'cut processing time in half') "
                f"or just 'it felt noticeably faster' are totally fine!"
            ),
            "impact": (
                f"No problem at all! What was the end result or real-world benefit once {project_name} was in place? "
                f"Did it save people time, automate a tedious process, or get used by active users?"
            )
        }

        q_text = fallback_clarifications.get(
            target_area,
            f"No problem! What I'm asking is: could you share a quick, plain-English detail about how {project_name} works? Even a single sentence is super helpful!"
        )

        return GeneratedQuestion(
            id=f"clarify_{target_area}_{uuid.uuid4().hex[:6]}",
            target_area=target_area,
            question=q_text,
            rationale=f"Explaining {target_area} in simple terms to help you answer."
        )

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
                question=f"In plain terms, what core problem or pain point was {project.name} built to solve?",
                rationale="Uncovers the problem statement and motivation simply."
            ),
            GeneratedQuestion(
                id="q_arch_1",
                target_area="architecture",
                question=f"How does data move through {project.name} from start to finish? (A quick high-level overview is plenty!)",
                rationale="Extracts system topology and component interactions."
            ),
            GeneratedQuestion(
                id="q_dec_1",
                target_area="technical_decisions",
                question=f"What was the main reason you picked {', '.join(project.technologies[:2]) if project.technologies else 'this stack'} over other alternatives?",
                rationale="Identifies decision-making criteria simply."
            )
        ]

    async def select_next_question(
        self,
        knowledge: ProjectKnowledge,
        coverage: KnowledgeCoverage,
        current_round: int,
        latest_question: str,
        latest_answer: str,
        history: List[Dict[str, str]],
        skip_area: Optional[str] = None
    ) -> FollowUpQuestionResult:
        """Analyze answer and select ONE high-value follow-up or stop."""
        
        # Check stopping conditions
        cov_dict = coverage.model_dump()
        sufficient_count = sum(1 for a in self.AREA_PRIORITIES if cov_dict.get(a) == CoverageLevel.SUFFICIENT.value)

        # 1. Max interview rounds reached (prevents interview from dragging on endlessly)
        if current_round >= settings.MAX_INTERVIEW_ROUNDS:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="Maximum configured interview rounds reached.",
                coverage_update={}
            )

        # 2. Check if all 8 dimensions are SUFFICIENT
        all_sufficient = all(cov_dict.get(a) == CoverageLevel.SUFFICIENT.value for a in self.AREA_PRIORITIES)
        if all_sufficient:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="All 8 technical dimensions sufficiently covered for an outstanding case study.",
                coverage_update={}
            )

        # 3. High completeness exit: if at least 7/8 dimensions are SUFFICIENT and we've gathered substantial depth
        if sufficient_count >= 7 and current_round >= 5:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="Comprehensive technical depth gathered across all key dimensions.",
                coverage_update={}
            )

        # Collect list of all uncovered areas
        uncovered_areas = [
            a for a in self.AREA_PRIORITIES
            if cov_dict.get(a) != CoverageLevel.SUFFICIENT.value
        ]

        # Prioritize areas that haven't been targeted yet in this interview to avoid repetitive loops
        asked_areas = {
            h.get("target_area")
            for h in history
            if h.get("target_area")
        }

        target_area = None
        # First pass: find highest priority area that is UNKNOWN or PARTIAL and hasn't been asked yet
        for area in self.AREA_PRIORITIES:
            if skip_area and area == skip_area:
                continue
            if area not in asked_areas and cov_dict.get(area) in (CoverageLevel.UNKNOWN.value, CoverageLevel.PARTIAL.value):
                target_area = area
                break

        # Second pass: if all unasked areas are exhausted, pick any remaining uncovered area not skipped
        if not target_area:
            for area in self.AREA_PRIORITIES:
                if skip_area and area == skip_area:
                    continue
                if cov_dict.get(area) in (CoverageLevel.UNKNOWN.value, CoverageLevel.PARTIAL.value):
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

        tech_str = ", ".join(knowledge.technologies) if knowledge.technologies else "tech stack"
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            project_name=knowledge.project_name,
            target_area=target_area,
            uncovered_areas=", ".join(uncovered_areas) if uncovered_areas else target_area,
            technologies=tech_str,
            accumulated_knowledge=json.dumps(knowledge.model_dump(exclude={"evidence"}), indent=2),
            coverage_state=json.dumps(cov_dict, indent=2),
            interview_history=history_text if history_text else "No prior history.",
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

        # Dynamic, tech-anchored fallback questions compelling rich details
        tech_two = ", ".join(knowledge.technologies[:2]) if knowledge.technologies else "your stack"
        fallback_questions = {
            "problem": f"What specific user pain point or technical bottleneck led to building {knowledge.project_name}, and why were existing tools inadequate?",
            "architecture": f"How does data flow end-to-end through {knowledge.project_name}, and what are the key architectural components connecting {tech_two}?",
            "technical_decisions": f"What was the main reason you chose {tech_two} over alternative tools, and what specific capability or constraint drove that decision?",
            "challenges": f"While building with {tech_two}, what was the trickiest bug, rate-limit, or performance hurdle you ran into, and how did it manifest?",
            "solutions": f"Specifically what technical mechanism, architecture tweak, or optimization did you use to resolve that hurdle with {tech_two}?",
            "tradeoffs": f"Every engineering choice involves trade-offs—what downsides, operational overhead, or limitations did you accept with {tech_two}?",
            "performance": f"Did you measure any latency, throughput, or scale metrics with {tech_two} (even ballpark estimates like ms or requests/sec)?",
            "impact": f"Once deployed, what concrete outcome, user adoption, or measurable business benefit did {knowledge.project_name} deliver?"
        }

        q_text = fallback_questions.get(
            target_area,
            f"Could you share a key technical mechanism or outcome from your work with {tech_two}?"
        )

        return FollowUpQuestionResult(
            has_next_question=True,
            question=GeneratedQuestion(
                id=f"q_{target_area}_{current_round + 1}",
                target_area=target_area,
                question=q_text,
                rationale=f"Gathers key details for {target_area}."
            ),
            coverage_update={target_area: CoverageLevel.PARTIAL}
        )
