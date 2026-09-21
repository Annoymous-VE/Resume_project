from datetime import datetime, timezone
from typing import Dict, Any, List
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import (
    ProjectKnowledge,
    ProblemKnowledge,
    ArchitectureKnowledge,
    ProvenanceFact,
    KnowledgeCoverage,
    CoverageLevel
)

class KnowledgeManager:
    """
    Manages structured ProjectKnowledge objects, ensuring provenance tracking,
    confidence accounting, non-destructive merging, and coverage evaluation.
    """

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

    def merge_answer(
        self,
        current_knowledge: ProjectKnowledge,
        target_area: str,
        answer_text: str,
        exchange_id: str
    ) -> ProjectKnowledge:
        """Merge facts from a user answer into structured knowledge with provenance."""
        now_str = datetime.now(timezone.utc).isoformat()

        # Add provenanced evidence item
        fact_item = ProvenanceFact(
            fact=answer_text.strip(),
            source=f"user_answer_{exchange_id}",
            confidence=0.98,
            category=target_area,
            created_at=now_str
        )
        current_knowledge.evidence.append(fact_item)

        # Categorize into knowledge fields
        clean_ans = answer_text.strip()
        if target_area == "problem":
            if not current_knowledge.problem.statement:
                current_knowledge.problem.statement = clean_ans
            else:
                current_knowledge.problem.context = f"{current_knowledge.problem.context or ''}\n{clean_ans}".strip()
        elif target_area == "architecture":
            if not current_knowledge.architecture.overview:
                current_knowledge.architecture.overview = clean_ans
            else:
                current_knowledge.architecture.components.append(clean_ans)
        elif target_area == "technical_decisions":
            current_knowledge.technical_decisions.append(clean_ans)
        elif target_area == "challenges":
            current_knowledge.challenges.append(clean_ans)
        elif target_area == "solutions":
            current_knowledge.solutions.append(clean_ans)
        elif target_area == "tradeoffs":
            current_knowledge.tradeoffs.append(clean_ans)
        elif target_area == "performance":
            current_knowledge.performance.append(clean_ans)
        elif target_area == "impact":
            current_knowledge.impact.append(clean_ans)
        else:
            current_knowledge.implementation.append(clean_ans)

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
                else (CoverageLevel.PARTIAL if knowledge.architecture.overview else CoverageLevel.UNKNOWN)
            ),
            technical_decisions=(
                CoverageLevel.SUFFICIENT if len(knowledge.technical_decisions) >= 2
                else (CoverageLevel.PARTIAL if len(knowledge.technical_decisions) == 1 else CoverageLevel.UNKNOWN)
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
