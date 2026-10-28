from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import (
    ProjectKnowledge,
    ProblemKnowledge,
    ArchitectureKnowledge,
    ProvenanceFact,
    KnowledgeCoverage,
    CoverageLevel,
    ExtractedAnswerFacts,
    ObstacleMitigationPair
)
from app.ai.prompts.question_generation import FACT_EXTRACTION_PROMPT
from app.ai.llm import BaseLLMClient

class KnowledgeManager:
    """
    Manages structured ProjectKnowledge objects, ensuring provenance tracking,
    confidence accounting, non-destructive merging, and coverage evaluation.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client

    def initialize_knowledge(self, project: ExtractedProject) -> ProjectKnowledge:
        """Create initial ProjectKnowledge object populated from resume facts."""
        evidence: List[ProvenanceFact] = []
        now_str = datetime.now(timezone.utc).isoformat()

        if project.description:
            evidence.append(ProvenanceFact(
                fact=project.description,
                source="resume",
                confidence=project.confidence,
                category="problem",
                created_at=now_str
            ))

        for tech in project.technologies:
            evidence.append(ProvenanceFact(
                fact=f"Used {tech}",
                source="resume",
                confidence=project.confidence,
                category="technologies",
                created_at=now_str
            ))

        for contrib in project.contributions:
            evidence.append(ProvenanceFact(
                fact=contrib,
                source="resume",
                confidence=project.confidence,
                category="implementation",
                created_at=now_str
            ))

        for outcome in project.outcomes:
            evidence.append(ProvenanceFact(
                fact=outcome,
                source="resume",
                confidence=project.confidence,
                category="impact",
                created_at=now_str
            ))

        return ProjectKnowledge(
            project_id=project.id,
            project_name=project.name,
            problem=ProblemKnowledge(
                statement=project.description if project.description else None,
                context="Extracted from resume experience."
            ),
            requirements=[],
            architecture=ArchitectureKnowledge(
                overview=f"Built with {', '.join(project.technologies)}" if project.technologies else None,
                components=[],
                data_flow=None
            ),
            technical_decisions=[],
            implementation=list(project.contributions),
            challenges=[],
            solutions=[],
            tradeoffs=[],
            performance=[],
            impact=list(project.outcomes),
            technologies=list(project.technologies),
            evidence=evidence
        )

    def _apply_fact_to_field(self, current_knowledge: ProjectKnowledge, category: str, fact_text: str):
        """Helper to route a single fact string to the appropriate knowledge field."""
        if category == "problem":
            if not current_knowledge.problem.statement:
                current_knowledge.problem.statement = fact_text
            else:
                current_knowledge.problem.context = f"{current_knowledge.problem.context or ''}\n{fact_text}".strip()
        elif category == "architecture":
            if not current_knowledge.architecture.overview:
                current_knowledge.architecture.overview = fact_text
            else:
                current_knowledge.architecture.components.append(fact_text)
        elif category == "technical_decisions":
            current_knowledge.technical_decisions.append(fact_text)
        elif category == "challenges":
            from app.services.interview_engine import InterviewEngine
            if not InterviewEngine.is_dismissive_reply(fact_text):
                current_knowledge.challenges.append(fact_text)
                if not any(p.obstacle == fact_text for p in current_knowledge.obstacle_mitigations):
                    current_knowledge.obstacle_mitigations.append(ObstacleMitigationPair(
                        obstacle=fact_text
                    ))
        elif category == "solutions":
            current_knowledge.solutions.append(fact_text)
            if current_knowledge.obstacle_mitigations:
                for pair in reversed(current_knowledge.obstacle_mitigations):
                    if not pair.measures_taken:
                        pair.measures_taken = fact_text
                        break
        elif category == "tradeoffs":
            current_knowledge.tradeoffs.append(fact_text)
        elif category == "performance":
            current_knowledge.performance.append(fact_text)
        elif category == "impact":
            current_knowledge.impact.append(fact_text)
        else:
            current_knowledge.implementation.append(fact_text)

    @staticmethod
    def is_explicit_negative_or_na_response(target_area: str, text: str) -> Optional[str]:
        """Detect whether the user provided an explicit, valid 'not applicable' or 'no formal metrics/tradeoffs' response.
        Returns a standardized, professional domain fact string if detected, or None."""
        if not text:
            return None
        clean = text.strip().lower().rstrip(".!?,")

        # 1. Tradeoffs dimension
        if target_area == "tradeoffs":
            tradeoff_markers = [
                "no major tradeoffs",
                "no tradeoffs",
                "no tradeoff",
                "no real tradeoffs",
                "not that many tradeoffs",
                "not many tradeoffs",
                "didn't face any tradeoffs",
                "did not face any tradeoffs",
                "no significant tradeoffs",
                "standard conventions; no major tradeoffs",
                "standard engineering conventions; no major tradeoffs",
                "none really",
                "not really any tradeoffs",
                "not really",
                "no compromises",
                "no real downsides",
                "no downsides"
            ]
            if clean in tradeoff_markers or any(m in clean for m in [
                "no major tradeoff", "no tradeoff", "not that many tradeoff", "not many tradeoff",
                "no real tradeoff", "no significant tradeoff", "standard engineering conventions", "no major tradeoffs"
            ]):
                return "Standard engineering conventions followed; no major architectural tradeoffs or compromises accepted."

        # 2. Performance dimension
        elif target_area == "performance":
            performance_markers = [
                "no exact numbers",
                "no exact performance benchmarks recorded",
                "no benchmarks recorded",
                "no performance benchmarks",
                "no benchmarks",
                "didn't measure performance",
                "did not measure performance",
                "didn't track performance",
                "did not track performance",
                "no metrics recorded",
                "no metrics",
                "no exact metrics",
                "no formal metrics",
                "not benchmarked",
                "wasn't benchmarked",
                "haven't benchmarked",
                "standard latency",
                "latency was not an issue",
                "speed was not an issue",
                "didn't track latency",
                "did not track latency"
            ]
            if clean in performance_markers or any(m in clean for m in [
                "no exact performance", "no benchmarks recorded", "no exact numbers",
                "no formal metrics", "didn't track latency", "didn't measure latency",
                "no metrics recorded", "standard response times", "no performance benchmarks"
            ]):
                return "Standard operational performance; no formal millisecond latency benchmarks or SLA metrics were tracked."

        # 3. Impact dimension
        elif target_area == "impact":
            impact_markers = [
                "internal use only",
                "for internal use",
                "personal project",
                "no commercial metrics",
                "no formal business metrics",
                "no user metrics",
                "used internally by the team"
            ]
            if any(m in clean for m in impact_markers):
                return "Designed for internal/team utility; automated workflow without formal public business metrics."

        return None

    async def extract_and_merge_answer(
        self,
        current_knowledge: ProjectKnowledge,
        target_area: str,
        answer_text: str,
        exchange_id: str
    ) -> ProjectKnowledge:
        """Extract multi-dimensional facts using LLM and merge them into structured knowledge."""
        clean_ans = answer_text.strip()
        if not clean_ans:
            return current_knowledge

        # If LLM is available, perform multi-entity extraction
        if self.llm:
            try:
                prompt = FACT_EXTRACTION_PROMPT.format(
                    developer_answer=clean_ans,
                    target_area=target_area
                )
                res = await self.llm.generate_structured(
                    prompt=prompt,
                    schema=ExtractedAnswerFacts,
                    system_prompt="You are a precise technical fact extractor for software engineering case studies."
                )
                if res is not None:
                    now_str = datetime.now(timezone.utc).isoformat()
                    from app.services.interview_engine import InterviewEngine

                    # 1. Process explicit obstacle_mitigations pairs if extracted
                    if res.obstacle_mitigations:
                        for pair in res.obstacle_mitigations:
                            if not pair.obstacle or InterviewEngine.is_dismissive_reply(pair.obstacle):
                                continue
                            current_knowledge.obstacle_mitigations.append(pair)
                            if pair.obstacle not in current_knowledge.challenges:
                                current_knowledge.challenges.append(pair.obstacle)
                            if pair.measures_taken and pair.measures_taken not in current_knowledge.solutions:
                                current_knowledge.solutions.append(pair.measures_taken)
                            current_knowledge.evidence.append(ProvenanceFact(
                                fact=pair.obstacle,
                                source="conversation",
                                confidence=0.98,
                                category="challenges",
                                created_at=now_str
                            ))
                            if pair.measures_taken:
                                current_knowledge.evidence.append(ProvenanceFact(
                                    fact=pair.measures_taken,
                                    source="conversation",
                                    confidence=0.98,
                                    category="solutions",
                                    created_at=now_str
                                ))

                    # 2. Process general facts
                    if res.facts:
                        valid_cats = {
                            "problem", "architecture", "technical_decisions",
                            "challenges", "solutions", "tradeoffs", "performance", "impact"
                        }
                        for item in res.facts:
                            cat = item.category if item.category in valid_cats else target_area
                            current_knowledge.evidence.append(ProvenanceFact(
                                fact=item.fact.strip(),
                                source="conversation",
                                confidence=0.98,
                                category=cat,
                                created_at=now_str
                            ))
                            self._apply_fact_to_field(current_knowledge, cat, item.fact.strip())
                    return current_knowledge
            except Exception:
                pass

        # 3. Check for explicit negative/NA acknowledgment if target area was not populated by LLM
        na_fact = self.is_explicit_negative_or_na_response(target_area, clean_ans)
        if na_fact:
            has_target_cat = any(e.category == target_area and e.source == "conversation" for e in current_knowledge.evidence)
            if not has_target_cat:
                now_str = datetime.now(timezone.utc).isoformat()
                current_knowledge.evidence.append(ProvenanceFact(
                    fact=na_fact,
                    source="conversation",
                    confidence=0.98,
                    category=target_area,
                    created_at=now_str
                ))
                self._apply_fact_to_field(current_knowledge, target_area, na_fact)
            return current_knowledge

        # Fallback to direct merge only if LLM is absent or failed, and text contains genuine factual content
        if not self._is_non_factual_input(clean_ans):
            return self.merge_answer(current_knowledge, target_area, clean_ans, exchange_id)
        return current_knowledge

    def _is_non_factual_input(self, text: str) -> bool:
        """Check if the text is a question, clarification request, or too brief to be a valid technical fact."""
        clean = text.lower().strip()
        if len(clean) < 3 or clean.endswith("?"):
            return True
        non_factual_markers = [
            "what do you mean", "can you explain", "could you explain", "don't understand",
            "dont understand", "i'm confused", "im confused", "what does", "give me an example",
            "what should i", "how should i", "help me", "skip", "pass", "no idea", "i don't know",
            "not sure", "n/a", "what is this", "huh", "pardon"
        ]
        return any(m in clean for m in non_factual_markers)

    def merge_answer(
        self,
        current_knowledge: ProjectKnowledge,
        target_area: str,
        answer_text: str,
        exchange_id: str
    ) -> ProjectKnowledge:
        """Merge facts from a user answer into structured knowledge with provenance (synchronous)."""
        now_str = datetime.now(timezone.utc).isoformat()
        clean_ans = answer_text.strip()
        na_fact = self.is_explicit_negative_or_na_response(target_area, clean_ans)
        if na_fact:
            fact_item = ProvenanceFact(
                fact=na_fact,
                source="conversation",
                confidence=0.98,
                category=target_area,
                created_at=now_str
            )
            current_knowledge.evidence.append(fact_item)
            self._apply_fact_to_field(current_knowledge, target_area, na_fact)
            return current_knowledge

        if self._is_non_factual_input(clean_ans):
            return current_knowledge

        # Add provenanced evidence item
        fact_item = ProvenanceFact(
            fact=clean_ans,
            source="conversation",
            confidence=0.98,
            category=target_area,
            created_at=now_str
        )
        current_knowledge.evidence.append(fact_item)
        self._apply_fact_to_field(current_knowledge, target_area, clean_ans)
        return current_knowledge

    def compute_coverage(self, knowledge: ProjectKnowledge) -> KnowledgeCoverage:
        """Determine coverage state for each knowledge area based on concrete facts."""
        return KnowledgeCoverage(
            problem=(
                CoverageLevel.SUFFICIENT if (
                    (knowledge.problem.statement and knowledge.problem.context)
                    or (knowledge.problem.statement and len(knowledge.problem.statement.strip()) >= 20)
                    or any(e.category == "problem" and len(e.fact.strip()) >= 15 for e in knowledge.evidence if e.source != "resume")
                )
                else (CoverageLevel.PARTIAL if knowledge.problem.statement else CoverageLevel.UNKNOWN)
            ),
            architecture=(
                CoverageLevel.SUFFICIENT if (
                    (knowledge.architecture.overview and len(knowledge.architecture.components) > 0)
                    or (knowledge.architecture.overview and len(knowledge.architecture.overview.strip()) >= 25)
                    or any(e.category == "architecture" and len(e.fact.strip()) >= 15 for e in knowledge.evidence if e.source != "resume")
                )
                else (CoverageLevel.PARTIAL if (knowledge.architecture.overview or len(knowledge.architecture.components) > 0) else CoverageLevel.UNKNOWN)
            ),
            technical_decisions=(
                CoverageLevel.SUFFICIENT if len(knowledge.technical_decisions) >= 1
                else CoverageLevel.UNKNOWN
            ),
            challenges=(
                CoverageLevel.SUFFICIENT if (len(knowledge.challenges) >= 1 or len(knowledge.obstacle_mitigations) >= 1)
                else CoverageLevel.UNKNOWN
            ),
            solutions=(
                CoverageLevel.SUFFICIENT if (len(knowledge.solutions) >= 1 or any(p.measures_taken for p in knowledge.obstacle_mitigations))
                else CoverageLevel.UNKNOWN
            ),
            tradeoffs=(
                CoverageLevel.SUFFICIENT if len(knowledge.tradeoffs) >= 1
                else CoverageLevel.UNKNOWN
            ),
            performance=(
                CoverageLevel.SUFFICIENT if len(knowledge.performance) >= 1
                else CoverageLevel.UNKNOWN
            ),
            impact=(
                CoverageLevel.SUFFICIENT if len(knowledge.impact) >= 1
                else CoverageLevel.UNKNOWN
            )
        )
