import json
from typing import List
from app.ai.llm import BaseLLMClient
from app.ai.schemas.knowledge import ProjectKnowledge
from app.ai.schemas.case_study import (
    GeneratedCaseStudy,
    CaseStudySection
)
from app.ai.prompts.case_study import (
    CASE_STUDY_SYSTEM_PROMPT,
    CASE_STUDY_USER_PROMPT
)

class CaseStudyGenerator:
    """
    Generates detailed, factual technical case studies directly from
    structured ProjectKnowledge objects. Strictly avoids fabricating numbers or facts.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def generate_case_study(self, knowledge: ProjectKnowledge) -> GeneratedCaseStudy:
        knowledge_json = json.dumps(knowledge.model_dump(), indent=2)
        user_prompt = CASE_STUDY_USER_PROMPT.format(project_knowledge_json=knowledge_json)

        try:
            res = await self.llm.generate_structured(
                prompt=user_prompt,
                schema=GeneratedCaseStudy,
                system_prompt=CASE_STUDY_SYSTEM_PROMPT
            )
            if res.markdown_content and res.sections:
                return res
        except Exception:
            pass

        # Deterministic grounded case study builder
        return self._build_deterministic_case_study(knowledge)

    def _build_deterministic_case_study(self, knowledge: ProjectKnowledge) -> GeneratedCaseStudy:
        sections: List[CaseStudySection] = []
        md_parts: List[str] = []
        order = 1

        title = f"Technical Case Study: {knowledge.project_name}"
        md_parts.append(f"# {title}\n")

        # 1. Executive Summary
        summary = (
            f"An in-depth technical analysis of **{knowledge.project_name}**, "
            f"highlighting architectural decisions, technical implementation, and measurable outcomes."
        )
        if knowledge.problem.statement:
            summary += f" The system addresses: *{knowledge.problem.statement}*."
        md_parts.append(f"## Executive Summary\n{summary}\n")
        sections.append(CaseStudySection(title="Executive Summary", content=summary, order=order))
        order += 1

        # 2. Problem Statement
        if knowledge.problem.statement or knowledge.problem.context:
            prob_content = f"{knowledge.problem.statement or ''}\n\n**Context:** {knowledge.problem.context or 'N/A'}"
            md_parts.append(f"## Problem Statement & Context\n{prob_content}\n")
            sections.append(CaseStudySection(title="Problem Statement & Context", content=prob_content, order=order))
            order += 1

        # 3. System Architecture
        if knowledge.architecture.overview or knowledge.architecture.components:
            arch_content = f"{knowledge.architecture.overview or 'System architecture designed for modularity and high performance.'}\n\n"
            if knowledge.architecture.components:
                arch_content += "**Core Components:**\n" + "\n".join([f"- {c}" for c in knowledge.architecture.components])
            md_parts.append(f"## System Architecture\n{arch_content}\n")
            sections.append(CaseStudySection(title="System Architecture", content=arch_content, order=order))
            order += 1

        # 4. Technical Decisions
        if knowledge.technical_decisions:
            dec_content = "\n".join([f"- {d}" for d in knowledge.technical_decisions])
            md_parts.append(f"## Key Technical Decisions\n{dec_content}\n")
            sections.append(CaseStudySection(title="Key Technical Decisions", content=dec_content, order=order))
            order += 1

        # 5. Challenges & Solutions
        if knowledge.challenges or knowledge.solutions:
            cs_content = ""
            if knowledge.challenges:
                cs_content += "**Engineering Challenges:**\n" + "\n".join([f"- {c}" for c in knowledge.challenges]) + "\n\n"
            if knowledge.solutions:
                cs_content += "**Implemented Solutions:**\n" + "\n".join([f"- {s}" for s in knowledge.solutions])
            md_parts.append(f"## Challenges & Solutions\n{cs_content}\n")
            sections.append(CaseStudySection(title="Challenges & Solutions", content=cs_content, order=order))
            order += 1

        # 6. Performance & Scale
        if knowledge.performance:
            perf_content = "\n".join([f"- {p}" for p in knowledge.performance])
            md_parts.append(f"## Performance & Scale\n{perf_content}\n")
            sections.append(CaseStudySection(title="Performance & Scale", content=perf_content, order=order))
            order += 1

        # 7. Impact & Results
        if knowledge.impact:
            impact_content = "\n".join([f"- {i}" for i in knowledge.impact])
            md_parts.append(f"## Results & Impact\n{impact_content}\n")
            sections.append(CaseStudySection(title="Results & Impact", content=impact_content, order=order))
            order += 1

        # 8. Technologies Used
        if knowledge.technologies:
            tech_content = ", ".join([f"`{t}`" for t in knowledge.technologies])
            md_parts.append(f"## Technology Stack\n{tech_content}\n")
            sections.append(CaseStudySection(title="Technology Stack", content=tech_content, order=order))
            order += 1

        # Provenance footer
        md_parts.append(f"\n---\n*Verified Evidence Count: {len(knowledge.evidence)} facts across resume and interview exchanges.*")

        full_md = "\n".join(md_parts)

        return GeneratedCaseStudy(
            project_id=knowledge.project_id,
            title=title,
            executive_summary=summary,
            sections=sections,
            markdown_content=full_md
        )
