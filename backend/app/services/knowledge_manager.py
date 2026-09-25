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
    ExtractedAnswerFacts
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
            current_knowledge.challenges.append(fact_text)
        elif category == "solutions":
            current_knowledge.solutions.append(fact_text)
        elif category == "tradeoffs":
            current_knowledge.tradeoffs.append(fact_text)
        elif category == "performance":
            current_knowledge.performance.append(fact_text)
        elif category == "impact":
            current_knowledge.impact.append(fact_text)
        else:
            current_knowledge.implementation.append(fact_text)

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
                    if res.facts:
                        now_str = datetime.now(timezone.utc).isoformat()
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
                CoverageLevel.SUFFICIENT if (knowledge.problem.statement and knowledge.problem.context)
                else (CoverageLevel.PARTIAL if knowledge.problem.statement else CoverageLevel.UNKNOWN)
            ),
            architecture=(
                CoverageLevel.SUFFICIENT if (knowledge.architecture.overview and len(knowledge.architecture.components) > 0)
                else (CoverageLevel.PARTIAL if (knowledge.architecture.overview or len(knowledge.architecture.components) > 0) else CoverageLevel.UNKNOWN)
            ),
            technical_decisions=(
                CoverageLevel.SUFFICIENT if len(knowledge.technical_decisions) >= 1
                else CoverageLevel.UNKNOWN
            ),
            challenges=(
                CoverageLevel.SUFFICIENT if len(knowledge.challenges) >= 1
                else CoverageLevel.UNKNOWN
            ),
            solutions=(
                CoverageLevel.SUFFICIENT if len(knowledge.solutions) >= 1
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

