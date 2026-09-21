import json
import logging
import re
from typing import List, Optional, Set
from app.ai.llm import BaseLLMClient
from app.ai.schemas.resume import DocumentRepresentation, DocumentBlock
from app.ai.schemas.project import ExtractedProject, ProjectExtractionResult
from app.ai.prompts.project_extraction import (
    PROJECT_EXTRACTION_SYSTEM_PROMPT,
    PROJECT_EXTRACTION_USER_PROMPT
)

logger = logging.getLogger(__name__)

class ProjectExtractor:
    """
    Identifies technical project entities from DocumentRepresentation.
    Doesn't depend solely on literal 'Projects' headers; analyzes semantics,
    bullet patterns, and technical actions across sections.
    """

    ACTION_VERBS: Set[str] = {
        "built", "implemented", "developed", "developing", "designed", "created",
        "engineered", "led", "managed", "automated", "spearheaded", "integrated",
        "responsible", "hands-on", "trained", "analyzed", "deployed", "scaled",
        "optimized", "configured", "maintained", "migrated", "collaborated"
    }

    TOOL_PREFIXES = (
        "tools &", "tool &", "tools:", "tech:", "technologies:", "technology:",
        "technique:", "techniques:", "built with:", "stack:", "environment:",
        "skills:", "libraries:"
    )

    TECH_KEYWORDS = {
        "python", "react", "react.js", "fastapi", "docker", "kubernetes", "aws", "gcp", "azure",
        "redis", "postgresql", "mongodb", "graphql", "kafka", "sql", "node.js",
        "typescript", "javascript", "go", "golang", "rust", "c++", "pytorch", "tensorflow",
        "langchain", "rag", "crag", "corrective rag", "streamlit", "pandas", "numpy",
        "scikit-learn", "random forest", "machine learning", "deep learning", "nlp", "llm"
    }

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def extract_projects(self, doc: DocumentRepresentation) -> List[ExtractedProject]:
        # First attempt LLM semantic extraction
        blocks_text = "\n".join([
            f"[{b.id}] ({b.type}, p.{b.page}, c.{b.column}) {b.text}"
            for b in doc.blocks
        ])

        user_prompt = PROJECT_EXTRACTION_USER_PROMPT.format(document_blocks=blocks_text)

        try:
            result = await self.llm.generate_structured(
                prompt=user_prompt,
                schema=ProjectExtractionResult,
                system_prompt=PROJECT_EXTRACTION_SYSTEM_PROMPT
            )
            if result.projects:
                logger.info("Successfully extracted %d projects via LLM.", len(result.projects))
                return result.projects
        except Exception as e:
            logger.warning("LLM extraction failed (%s). Falling back to deterministic heuristic extraction.", e)

        return self._heuristic_extraction(doc.blocks)

    def _clean_project_title(self, line: str) -> str:
        """Strip date annotations and trailing delimiter characters from project title lines."""
        cleaned = re.sub(r"\(?\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b.*$", "", line, flags=re.I)
        cleaned = re.sub(r"\(?\d{1,2}/\d{2,4}\s*[-–—\s]*(?:present|\d{1,2}/\d{2,4})?\)?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\(?\b\d{4}\s*[-–—\s]*(?:present|\d{4})\)?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"[\s|\–\—\-]+$", "", cleaned).strip()

        # If pipe exists (e.g. "Project Name | Python, Kafka"), take first part as title
        if "|" in cleaned:
            parts = cleaned.split("|", maxsplit=1)
            cleaned = parts[0].strip()

        return cleaned

    def _is_title_candidate(self, raw_text: str) -> bool:
        """Check whether a line represents a project title."""
        title = self._clean_project_title(raw_text)
        words = title.split()
        if not words or len(words) > 7:
            return False

        # Must not end with terminal sentence punctuation
        if title.endswith((".", ":", "!", "?", ";")):
            return False

        # First word must not be lowercase
        if title[0].islower():
            return False

        # First word must not be an action verb
        first_word = words[0].lower().strip("•-*►▫▪–—")
        if first_word in self.ACTION_VERBS:
            return False

        lower = raw_text.lower().strip()
        if any(lower.startswith(p) for p in self.TOOL_PREFIXES):
            return False

        # Must not be single bullet character
        if raw_text in ("•", "-", "*", "–", "—", "►", "▪", "▫", "✓", ""):
            return False

        return True

    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technologies from a text line."""
        found = []
        lower = text.lower()
        for tech in self.TECH_KEYWORDS:
            pattern = rf"\b{re.escape(tech)}\b"
            if re.search(pattern, lower):
                found.append(tech.title())

        # If line has colon (e.g. "Tools & Techniques : Python, Langchain, Corrective RAG")
        if ":" in text:
            after_colon = text.split(":", maxsplit=1)[1]
            tokens = [t.strip() for t in re.split(r"[,|;]", after_colon) if t.strip()]
            for token in tokens:
                if len(token.split()) <= 4 and token not in found:
                    found.append(token)

        # De-duplicate case-insensitively
        seen = set()
        deduped = []
        for t in found:
            t_norm = t.lower()
            if t_norm not in seen:
                seen.add(t_norm)
                deduped.append(t)
        return deduped

    def _heuristic_extraction(self, blocks: List[DocumentBlock]) -> List[ExtractedProject]:
        """Deterministic heuristic extraction if LLM is unavailable or fails."""
        projects: List[ExtractedProject] = []
        current_project: Optional[dict] = None
        in_project_section = False
        project_count = 0

        for block in blocks:
            text = block.text.strip()
            lower = text.lower()

            # Section heading check
            if block.type == "heading":
                if any(w in lower for w in ["project", "selected work", "portfolio", "built", "key projects"]):
                    in_project_section = True
                    continue
                elif any(w in lower for w in ["education", "skills", "experience", "certifications", "languages", "interests", "awards"]):
                    in_project_section = False
                    if current_project and current_project["name"]:
                        projects.append(self._build_project_obj(current_project))
                        current_project = None
                    continue

            if in_project_section:
                # Check for explicit tool/technique lines
                if any(lower.startswith(p) for p in self.TOOL_PREFIXES):
                    if current_project:
                        techs = self._extract_technologies(text)
                        for t in techs:
                            if t.lower() not in [x.lower() for x in current_project["technologies"]]:
                                current_project["technologies"].append(t)
                    continue

                # Ignore empty or solitary bullet characters
                if text in ("•", "-", "*", "–", "—", "") or len(text) <= 1:
                    continue

                # Check if this line is a project title candidate
                if self._is_title_candidate(text):
                    if current_project and current_project["name"]:
                        projects.append(self._build_project_obj(current_project))

                    project_count += 1
                    title = self._clean_project_title(text)

                    # Extract any inline technologies from title line (e.g. "Platform | Python, Go")
                    inline_techs = []
                    if "|" in text:
                        inline_techs = self._extract_technologies(text.split("|", 1)[1])

                    current_project = {
                        "id": f"proj_{project_count}",
                        "name": title,
                        "description": "",
                        "technologies": inline_techs,
                        "contributions": [],
                        "outcomes": [],
                        "links": [w for w in text.split() if w.startswith("http")],
                        "source_blocks": [block.id]
                    }
                    continue

                # If inside a project, capture description/bullets/tools
                if current_project:
                    current_project["source_blocks"].append(block.id)

                    # Extract links
                    for word in text.split():
                        if word.startswith("http") and word not in current_project["links"]:
                            current_project["links"].append(word)

                    # Extract tech keywords mentioned in description
                    for tech in self._extract_technologies(text):
                        if tech.lower() not in [x.lower() for x in current_project["technologies"]]:
                            current_project["technologies"].append(tech)

                    # Clean leading bullet symbols from description/contribution text
                    cleaned_body = re.sub(r"^[•\-\*–—►▫▪✓\s]+", "", text).strip()
                    if not current_project["description"]:
                        current_project["description"] = cleaned_body
                    else:
                        current_project["contributions"].append(cleaned_body)

                    # Detect outcomes/metrics
                    if any(m in lower for m in ["reduced", "increased", "improved", "latency", "%", "throughput", "saved", "achieved"]):
                        if cleaned_body not in current_project["outcomes"]:
                            current_project["outcomes"].append(cleaned_body)

        if current_project and current_project["name"]:
            projects.append(self._build_project_obj(current_project))

        # If still no projects detected (e.g. resume had no 'Projects' section heading),
        # scan for technical projects embedded in experience
        if not projects:
            projects = self._extract_projects_from_experience(blocks)

        # Clean & de-duplicate projects
        cleaned_projects: List[ExtractedProject] = []
        seen_names = set()
        for p in projects:
            if not p.name or p.name.lower() in seen_names or len(p.name) < 3:
                continue
            seen_names.add(p.name.lower())
            cleaned_projects.append(p)

        return cleaned_projects

    def _extract_projects_from_experience(self, blocks: List[DocumentBlock]) -> List[ExtractedProject]:
        """Fallback to detect projects mentioned within general experience when no project heading exists."""
        projects = []
        proj_idx = 0
        for block in blocks:
            text = block.text.strip()
            # Look for lines starting with strong build/implement actions
            if any(text.lower().startswith(v) for v in ["built an", "built a", "implemented an", "implemented a", "developed an", "developed a", "designed and built"]):
                proj_idx += 1
                cleaned = re.sub(r"^[•\-\*–—►▫▪✓\s]+", "", text).strip()
                # Derive title from the action clause
                title_match = re.match(r"(?:built|implemented|developed|designed)\s+(?:an?|the)?\s*([A-Za-z0-9\-\s]{3,40}?)(?:\s+that|\s+with|\s+to|\s+using|\.|$)", cleaned, re.I)
                name = title_match.group(1).strip().title() if title_match else f"Technical Project {proj_idx}"
                techs = self._extract_technologies(text)

                projects.append(ExtractedProject(
                    id=f"proj_exp_{proj_idx}",
                    name=name,
                    description=cleaned,
                    technologies=techs,
                    contributions=[cleaned],
                    outcomes=[cleaned] if any(m in text.lower() for m in ["reduced", "improved", "%", "latency"]) else [],
                    links=[w for w in text.split() if w.startswith("http")],
                    source_blocks=[block.id],
                    confidence=0.80
                ))

        if not projects:
            tech_bullets = [b.text for b in blocks if b.type == "bullet"]
            all_text = " ".join([b.text for b in blocks])
            projects.append(ExtractedProject(
                id="proj_default",
                name="Core Engineering Project",
                description="Technical software project identified from engineering work.",
                technologies=self._extract_technologies(all_text),
                contributions=tech_bullets[:3],
                outcomes=tech_bullets[3:5],
                links=[],
                source_blocks=[b.id for b in blocks[:5]],
                confidence=0.75
            ))

        return projects

    def _build_project_obj(self, data: dict) -> ExtractedProject:
        return ExtractedProject(
            id=data["id"],
            name=data["name"] or "Untitled Project",
            description=data.get("description") or None,
            technologies=data.get("technologies", []),
            contributions=data.get("contributions", []),
            outcomes=data.get("outcomes", []),
            links=data.get("links", []),
            source_blocks=data.get("source_blocks", []),
            confidence=0.90
        )
