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
        """Detect whether the user is asking for clarification, explanation, or verifying their understanding."""
        if not text:
            return False
        clean = text.strip().lower()

        clarification_patterns = [
            # Direct requests for explanation / clarification
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
            r"explain what",
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
            r"help me understand",
            r"help me",
            r"what are alternatives",
            r"what is alternative",
            r"why do you ask",
            r"huh\?",
            r"pardon\?",
            # Verification of understanding / confirmation inquiries
            r"^(?:so\s+)?(?:do\s+you|you)\s+mean\b",
            r"^(?:are\s+you|you\s+are)\s+(?:asking|looking for|referring to|inquiring about)\b",
            r"^is\s+(?:this|that)\s+(?:about|asking|referring to|related to)\b",
            r"^does\s+(?:this|that)\s+(?:mean|refer to)\b",
            r"^am\s+i\s+(?:understanding|getting)(?:\s+(?:this|it))?\s+(?:right|correctly)\b",
            r"\bam\s+i\s+understanding\b",
            r"^(?:is\s+my|my)\s+understanding\s+(?:correct|right)\b",
            r"^correct\s+me\s+if\s+i'?m\s+wrong\b",
            r"^(?:just\s+to\s+)?(?:clarify|confirm)\b",
            r"^(?:should|can|could)\s+i\s+(?:talk|mention|explain|focus|write)\s+about\b",
            r"^meaning\s*[:?]?\s*",
            r"^would\s+that\s+be\b",
            r"^like\s+(?:whether|if)\s+we\b",
            r"\byou\s+mean\b",
            r"\bmean\s+by\b",
            r"\brefer\s+to\b",
            r"\breferring\s+to\b",
            r"\basking\s+about\b",
            r"\blooking\s+for\b"
        ]
        for pattern in clarification_patterns:
            if re.search(pattern, clean):
                return True

        # If it's a short/mid-sized question ending in ? and has inquiry or verification words
        if clean.endswith("?") and len(clean.split()) <= 25:
            if any(w in clean for w in [
                "what", "why", "how", "which", "who", "can you", "could you", "mean",
                "asking", "looking for", "example", "refer", "referring", "explain", "clarify"
            ]):
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

    @staticmethod
    def is_dismissive_reply(text: str) -> bool:
        """Detect whether the user provided a dismissive, superficial, or non-informative reply to an obstacle inquiry."""
        if not text:
            return True
        clean = text.strip().lower().rstrip(".!?,")
        dismissive_phrases = {
            "everything went smoothly",
            "everything went smooth",
            "everything was smooth",
            "everything went well",
            "everything worked smoothly",
            "everything worked fine",
            "everything worked as expected",
            "everything was fine",
            "all went smoothly",
            "all was smooth",
            "went smoothly",
            "smooth sailing",
            "it was smooth",
            "it was easy",
            "it went smoothly",
            "no issues",
            "no issue",
            "no problems",
            "no problem",
            "no challenges",
            "no challenge",
            "no obstacles",
            "no obstacle",
            "no bottlenecks",
            "no bottleneck",
            "no failure modes",
            "no bugs",
            "no blockers",
            "no major issues",
            "no major problems",
            "no major challenges",
            "no major obstacles",
            "no major bottlenecks",
            "no real issues",
            "no real challenges",
            "no real obstacles",
            "no critical issues",
            "none",
            "none really",
            "not really",
            "nothing",
            "nothing really",
            "nothing special",
            "nothing went wrong",
            "nothing broke",
            "there were no issues",
            "there was no issue",
            "there were no problems",
            "there were no challenges",
            "there were no obstacles",
            "there was no problem",
            "we had no issues",
            "we faced no issues",
            "we faced no problems",
            "we didn't face any issues",
            "we did not face any issues",
            "didn't face any issues",
            "we didn't have any issues",
            "we did not have any issues",
            "didn't have any issues",
            "we didn't face any problems",
            "didn't encounter any issues",
            "did not encounter any issues",
            "we didn't run into any issues",
            "it was straightforward",
            "pretty straightforward",
            "very straightforward",
            "fairly straightforward",
            "n/a",
            "na"
        }
        if clean in dismissive_phrases:
            return True

        dismissive_patterns = [
            r"^(?:everything|it all|all of it)\s+(?:went|was|worked)\s+(?:smoothly|smooth|fine|great|well|as expected)",
            r"^(?:there\s+were|there\s+was|we\s+had|we\s+faced)\s+no\s+(?:issues|problems|challenges|obstacles|bottlenecks|bugs|hurdles|blockers)",
            r"^(?:did\s*n'?t|did\s+not|had\s+no)\s+(?:face|have|encounter|run\s+into)\s+(?:any|major|real)\s+(?:issues|problems|challenges|obstacles|bottlenecks)",
            r"^no\s+(?:real|major|significant|particular|technical)\s+(?:issues|problems|challenges|obstacles|bottlenecks|hurdles|blockers)",
            r"^(?:smooth\s+sailing|nothing\s+went\s+wrong|nothing\s+really|not\s+really\s+any|it\s+was\s+smooth)",
        ]
        for pattern in dismissive_patterns:
            if re.search(pattern, clean):
                return True

        return False

    def generate_obstacle_escalation_question(
        self,
        technologies: Optional[List[str]] = None,
        round_num: int = 1
    ) -> GeneratedQuestion:
        """Generate category escalation follow-up when candidate gives a superficial/dismissive reply to obstacle inquiry."""
        prompt_text = (
            "Even well-designed architectures face constraints like API rate limits, "
            "database locks, slow queries, or third-party integration bugs. Which of these did you experience?"
        )
        return GeneratedQuestion(
            id=f"q_obstacle_escalation_{round_num}_{uuid.uuid4().hex[:6]}",
            target_area="challenges",
            question=prompt_text,
            rationale="Escalates superficial response with concrete category prompts."
        )

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
                if clean_text and len(clean_text) > 15 and not clean_text.startswith("#"):
                    return GeneratedQuestion(
                        id=f"clarify_{target_area}_{uuid.uuid4().hex[:6]}",
                        target_area=target_area,
                        question=clean_text,
                        rationale="Clarification & guidance — share your thoughts whenever you're ready."
                    )
            except Exception:
                pass

        # Check if the user is verifying their understanding (and not just asking "what do you mean?")
        uq_clean = user_query.strip().lower()
        is_verification = False
        if not re.search(r"\b(?:what|explain)\s+(?:do\s+you|you)\s+mean\b", uq_clean):
            verification_patterns = [
                r"^(?:so\s+)?(?:do\s+you|you)\s+mean\b",
                r"^(?:are\s+you|you\s+are)\s+(?:asking|looking for|referring to)\b",
                r"^is\s+(?:this|that)\s+(?:about|asking|referring to)\b",
                r"^does\s+(?:this|that)\s+(?:mean|refer to)\b",
                r"^am\s+i\s+(?:understanding|getting)\b",
                r"^(?:is\s+my|my)\s+understanding\b",
                r"^correct\s+me\b",
                r"\bdo\s+you\s+mean\b",
                r"\bare\s+you\s+asking\b",
                r"\bis\s+this\s+about\b",
            ]
            is_verification = any(re.search(p, uq_clean) for p in verification_patterns)

        if is_verification:
            verification_clarifications = {
                "technical_decisions": (
                    f"Yes, exactly! I'm curious what led you to pick {tech_str} over other alternatives for {project_name}. "
                    f"Even a brief reason like performance, built-in features, or familiarity works great. "
                    f"Take your time and share whenever you're ready!"
                ),
                "problem": (
                    f"Yes, exactly! I'm interested in the core pain point or user problem that motivated {project_name}, "
                    f"and why existing solutions weren't enough. Feel free to explain in your own words!"
                ),
                "architecture": (
                    f"Yes, that's right! I'm looking for a high-level picture of how the components in {project_name} "
                    f"talk to each other (for instance, frontend -> API -> {tech_str} -> database). "
                    f"A brief walkthrough is plenty!"
                ),
                "challenges": (
                    f"Yes, exactly! I'm asking about the trickiest technical hurdle or unexpected bug you ran into while working with {tech_str}. "
                    f"For example, slow queries, concurrency issues, or third-party limits. Whenever you're ready, share what you encountered!"
                ),
                "solutions": (
                    f"Yes, spot on! I'm curious how you resolved or worked around that hurdle—such as adding caching, optimizing code, "
                    f"or tweaking architecture. Feel free to describe whatever steps you took!"
                ),
                "tradeoffs": (
                    f"Yes, exactly! In engineering, every technical choice comes with pros and cons. "
                    f"I'm curious about any downsides or compromises you had to accept with {tech_str}."
                ),
                "performance": (
                    f"Yes, exactly! Any ballpark figures on speed, throughput, or capacity (like response times or handled requests), "
                    f"or even general observations like 'noticeably faster' are great."
                ),
                "impact": (
                    f"Yes, that's right! What was the tangible result or benefit once {project_name} went live—like saving time, "
                    f"handling user traffic, or automating manual work?"
                )
            }
            if target_area in verification_clarifications:
                return GeneratedQuestion(
                    id=f"clarify_{target_area}_{uuid.uuid4().hex[:6]}",
                    target_area=target_area,
                    question=verification_clarifications[target_area],
                    rationale="Confirming your understanding and clarifying the question."
                )

        # Friendly, supportive general explanations tailored to the area
        fallback_clarifications = {
            "technical_decisions": (
                f"No worries at all! In plain words: out of all the tools out there, what made you choose {tech_str} for {project_name}? "
                f"For example, was it for speed, ease of use, team familiarity, or a specific feature? A quick reason is plenty!"
            ),
            "problem": (
                f"Happy to explain! In simple terms: what real-world headache or manual hassle was {project_name} built to solve, "
                f"and why couldn't existing tools handle it? Feel free to share in everyday words."
            ),
            "architecture": (
                f"No problem! What I mean is: if you drew a simple whiteboard sketch of {project_name}, "
                f"what are the main building blocks and how do they communicate? (e.g. Web UI -> Backend -> Database). A quick overview is great!"
            ),
            "challenges": (
                f"All good! Every project hits unexpected friction or bugs—like slow database queries, rate limits, or concurrency issues. "
                f"What was the toughest technical hurdle you bumped into with {tech_str}?"
            ),
            "solutions": (
                f"Happy to clarify! How did you end up fixing or working around that technical hurdle? "
                f"For instance, did you add caching, rewrite a query, switch a library, or reconfigure settings? Any concrete step helps!"
            ),
            "tradeoffs": (
                f"No worries! Every tech choice involves compromises. What was a downside or limitation with this setup "
                f"(for instance, extra maintenance, steeper learning curve, or memory usage)?"
            ),
            "performance": (
                f"Happy to explain! Did you notice or track any speed, throughput, or capacity metrics? "
                f"Even ballpark estimates (like 'under 200ms' or 'processed thousands of records') or 'felt much faster' are totally fine!"
            ),
            "impact": (
                f"No problem at all! What was the end result or real-world benefit once {project_name} was in place? "
                f"Did it save people time, automate a tedious process, or support active users?"
            )
        }

        q_text = fallback_clarifications.get(
            target_area,
            f"No problem! Could you share a quick, plain-English detail about how {project_name} works? Even a single sentence is super helpful!"
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
                question=f"To kick things off, what was the core problem or user pain point {project.name} was built to solve?",
                rationale="Uncovers the problem statement and motivation simply."
            ),
            GeneratedQuestion(
                id="q_arch_1",
                target_area="architecture",
                question=f"At a high level, how does data flow through {project.name} from the user to your backend services?",
                rationale="Extracts system topology and component interactions."
            ),
            GeneratedQuestion(
                id="q_dec_1",
                target_area="technical_decisions",
                question=f"What made you choose {', '.join(project.technologies[:2]) if project.technologies else 'this tech stack'} over other options you might have considered?",
                rationale="Identifies decision-making criteria simply."
            )
        ]

    @classmethod
    def has_concrete_obstacle(cls, knowledge: Optional[ProjectKnowledge], coverage: Optional[KnowledgeCoverage] = None) -> bool:
        """Check whether at least one concrete obstacle/challenge has been gathered."""
        if not knowledge:
            return False
        if any(bool(p and p.obstacle and p.obstacle.strip() and not cls.is_dismissive_reply(p.obstacle)) for p in (knowledge.obstacle_mitigations or [])):
            return True
        if any(bool(c and c.strip() and not cls.is_dismissive_reply(c)) for c in (knowledge.challenges or [])):
            return True
        if knowledge.evidence:
            if any(e.category == "challenges" and len(e.fact.strip()) > 5 and not cls.is_dismissive_reply(e.fact) for e in knowledge.evidence):
                return True
        if coverage:
            cov_dict = coverage.model_dump()
            if cov_dict.get("challenges") in (CoverageLevel.PARTIAL.value, CoverageLevel.SUFFICIENT.value):
                if knowledge.challenges and all(cls.is_dismissive_reply(c) for c in knowledge.challenges):
                    return False
                return True
        return False

    @classmethod
    def has_concrete_mitigation(cls, knowledge: Optional[ProjectKnowledge], coverage: Optional[KnowledgeCoverage] = None) -> bool:
        """Check whether at least one concrete mitigation/solution has been gathered."""
        if not knowledge:
            return False
        if any(bool(p and p.measures_taken and len(p.measures_taken.strip()) > 5) for p in (knowledge.obstacle_mitigations or [])):
            return True
        if any(bool(s and s.strip()) for s in (knowledge.solutions or [])):
            return True
        if knowledge.evidence:
            if any(e.category == "solutions" and len(e.fact.strip()) > 5 for e in knowledge.evidence):
                return True
        if coverage:
            cov_dict = coverage.model_dump()
            if cov_dict.get("solutions") in (CoverageLevel.PARTIAL.value, CoverageLevel.SUFFICIENT.value):
                return True
        return False

    @classmethod
    def has_obstacle_and_mitigation(cls, knowledge: Optional[ProjectKnowledge], coverage: Optional[KnowledgeCoverage] = None) -> bool:
        """Check whether BOTH a concrete obstacle and its corresponding mitigation have been gathered."""
        return cls.has_concrete_obstacle(knowledge, coverage) and cls.has_concrete_mitigation(knowledge, coverage)

    async def select_next_question(
        self,
        knowledge: ProjectKnowledge,
        coverage: KnowledgeCoverage,
        current_round: int,
        latest_question: str,
        latest_answer: str,
        history: List[Dict[str, str]],
        skip_area: Optional[str] = None,
        force_continue: bool = False
    ) -> FollowUpQuestionResult:
        """Analyze answer and select ONE high-value follow-up or stop."""
        
        # Check stopping conditions & Mandatory Obstacle Phase-Gate
        cov_dict = coverage.model_dump()
        sufficient_count = sum(1 for a in self.AREA_PRIORITIES if cov_dict.get(a) == CoverageLevel.SUFFICIENT.value)

        has_obstacle = self.has_concrete_obstacle(knowledge, coverage)
        has_mitigation = self.has_concrete_mitigation(knowledge, coverage)
        obstacle_gate_passed = has_obstacle and has_mitigation

        # Check if all 8 dimensions are SUFFICIENT (and obstacle phase-gate passed) -> 100% complete
        all_sufficient = all(cov_dict.get(a) == CoverageLevel.SUFFICIENT.value for a in self.AREA_PRIORITIES)
        if all_sufficient and obstacle_gate_passed:
            return FollowUpQuestionResult(
                has_next_question=False,
                stop_reason="All 8 technical dimensions are 100% completed and sufficiently covered for an outstanding case study.",
                coverage_update={}
            )

        if not force_continue:
            # Hard upper ceiling to prevent infinite loops if candidate continuously refuses to provide an obstacle
            max_hard_ceiling = settings.MAX_INTERVIEW_ROUNDS + 2
            if current_round >= max_hard_ceiling:
                return FollowUpQuestionResult(
                    has_next_question=False,
                    stop_reason="Maximum configured interview rounds reached.",
                    coverage_update={}
                )

            # High completeness exit: if at least 7/8 dimensions are SUFFICIENT and we've gathered substantial depth
            if sufficient_count >= 7 and current_round >= 5 and obstacle_gate_passed:
                return FollowUpQuestionResult(
                    has_next_question=False,
                    stop_reason="Comprehensive technical depth gathered across all key dimensions.",
                    coverage_update={}
                )

            # Standard max interview rounds reached: allows stopping only if obstacle phase gate has passed
            if current_round >= settings.MAX_INTERVIEW_ROUNDS and obstacle_gate_passed:
                return FollowUpQuestionResult(
                    has_next_question=False,
                    stop_reason="Maximum configured interview rounds reached.",
                    coverage_update={}
                )
        else:
            # In force_continue mode, allow continuing until 100% coverage with an extreme safety bound
            if current_round >= 30:
                return FollowUpQuestionResult(
                    has_next_question=False,
                    stop_reason="Maximum extension rounds reached.",
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

        # MANDATORY OBSTACLE PHASE-GATE ENFORCEMENT:
        # If early stopping conditions would have triggered OR after foundational context (current_round >= 3),
        # prioritize enforcing the obstacle and mitigation phase gate.
        need_obstacle = not has_obstacle and skip_area != "challenges"
        need_mitigation = has_obstacle and not has_mitigation and skip_area != "solutions"

        if (all_sufficient or sufficient_count >= 6 or current_round >= 3) and (need_obstacle or need_mitigation):
            if need_obstacle:
                target_area = "challenges"
            elif need_mitigation:
                target_area = "solutions"

        # First pass: find highest priority area that is UNKNOWN or PARTIAL and hasn't been asked yet
        if not target_area:
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

        # Third pass: Phase-Gate final check
        # If all uncovered areas are marked sufficient but obstacle gate is not passed,
        # DO NOT STOP! Force query for the missing obstacle or mitigation.
        if not target_area:
            if not has_obstacle and skip_area != "challenges":
                target_area = "challenges"
            elif not has_mitigation and skip_area != "solutions":
                target_area = "solutions"
            elif uncovered_areas:
                target_area = uncovered_areas[0]
            else:
                return FollowUpQuestionResult(
                    has_next_question=False,
                    stop_reason="All 8 technical dimensions are 100% completed and sufficiently covered for an outstanding case study.",
                    coverage_update={}
                )

        # Fallback escalation for superficial answers:
        # If targeting challenges and the candidate gave a dismissive reply (e.g. 'everything went smoothly'),
        # automatically follow up with the category prompt.
        if target_area == "challenges" and self.is_dismissive_reply(latest_answer):
            return FollowUpQuestionResult(
                has_next_question=True,
                question=self.generate_obstacle_escalation_question(
                    technologies=knowledge.technologies,
                    round_num=current_round + 1
                ),
                coverage_update={"challenges": CoverageLevel.UNKNOWN}
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

        # Natural, conversational fallback questions asking exactly ONE question
        tech_two = ", ".join(knowledge.technologies[:2]) if knowledge.technologies else "your stack"
        fallback_questions = {
            "problem": f"What was the core problem or user pain point that {knowledge.project_name} was created to solve?",
            "architecture": f"At a high level, how does data flow through {knowledge.project_name} between {tech_two} and your storage?",
            "technical_decisions": f"What led you to choose {tech_two} over other alternatives for this project?",
            "challenges": f"When building with {tech_two}, what was the trickiest technical hurdle or bottleneck you ran into?",
            "solutions": f"How did you end up solving or working around that technical challenge?",
            "tradeoffs": f"Were there any trade-offs or limitations with using {tech_two} that you had to accept?",
            "performance": f"Did you observe or measure any performance metrics with {tech_two}, like latency or throughput (even rough ballpark numbers)?",
            "impact": f"Once {knowledge.project_name} was up and running, what was the most meaningful impact or outcome it delivered?"
        }

        q_text = fallback_questions.get(
            target_area,
            f"Could you share a bit more detail about how you worked with {tech_two}?"
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
