from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CoverageLevel(str, Enum):
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"
    SUFFICIENT = "SUFFICIENT"

class ProvenanceFact(BaseModel):
    fact: str
    source: str = Field(..., description="e.g., 'resume', 'user_answer_1', 'system_inference'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    category: Optional[str] = None
    created_at: Optional[str] = None

class ProblemKnowledge(BaseModel):
    statement: Optional[str] = None
    context: Optional[str] = None
    motivation: Optional[str] = None

class ArchitectureKnowledge(BaseModel):
    overview: Optional[str] = None
    components: List[str] = Field(default_factory=list)
    data_flow: Optional[str] = None

class ProjectKnowledge(BaseModel):
    project_id: str
    project_name: str
    problem: ProblemKnowledge = Field(default_factory=ProblemKnowledge)
    requirements: List[str] = Field(default_factory=list)
    architecture: ArchitectureKnowledge = Field(default_factory=ArchitectureKnowledge)
    technical_decisions: List[str] = Field(default_factory=list)
    implementation: List[str] = Field(default_factory=list)
    challenges: List[str] = Field(default_factory=list)
    solutions: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    performance: List[str] = Field(default_factory=list)
    impact: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    evidence: List[ProvenanceFact] = Field(default_factory=list)

class KnowledgeCoverage(BaseModel):
    problem: CoverageLevel = CoverageLevel.UNKNOWN
    architecture: CoverageLevel = CoverageLevel.UNKNOWN
    technical_decisions: CoverageLevel = CoverageLevel.UNKNOWN
    challenges: CoverageLevel = CoverageLevel.UNKNOWN
    solutions: CoverageLevel = CoverageLevel.UNKNOWN
    tradeoffs: CoverageLevel = CoverageLevel.UNKNOWN
    performance: CoverageLevel = CoverageLevel.UNKNOWN
    impact: CoverageLevel = CoverageLevel.UNKNOWN

class ExtractedFactItem(BaseModel):
    category: str = Field(..., description="One of: problem, architecture, technical_decisions, challenges, solutions, tradeoffs, performance, impact")
    fact: str = Field(..., description="Concise technical fact extracted from candidate answer")

class ExtractedAnswerFacts(BaseModel):
    facts: List[ExtractedFactItem] = Field(default_factory=list)

