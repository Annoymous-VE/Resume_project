from typing import List, Optional
from pydantic import BaseModel, Field

class CaseStudySection(BaseModel):
    title: str
    content: str
    order: int
    omitted: bool = False
    omission_reason: Optional[str] = None

class GeneratedCaseStudy(BaseModel):
    project_id: str
    title: str
    executive_summary: str
    sections: List[CaseStudySection] = Field(default_factory=list)
    markdown_content: str
