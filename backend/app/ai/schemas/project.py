from typing import List, Optional
from pydantic import BaseModel, Field

class ExtractedProject(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    contributions: List[str] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    source_blocks: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class ProjectExtractionResult(BaseModel):
    projects: List[ExtractedProject] = Field(default_factory=list)
    extraction_summary: Optional[str] = None
