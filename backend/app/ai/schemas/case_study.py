from typing import List, Optional
from pydantic import BaseModel, Field

class CaseStudySection(BaseModel):
    title: str = Field(..., description="Section title, e.g. 'Executive Summary & Overview', 'Technologies & Tools'")
    format_type: str = Field(
        default="bullets",
        description="Format style applied: 'paragraph' (cohesive narrative prose), 'bullets' (itemized/categorized list), or 'hybrid' (prose intro followed by bullet points)"
    )
    content: str = Field(..., description="Markdown content formatted according to the universal section guidelines")
    order: int
    omitted: bool = False
    omission_reason: Optional[str] = None

class GeneratedCaseStudy(BaseModel):
    project_id: str
    title: str
    executive_summary: str
    sections: List[CaseStudySection] = Field(default_factory=list)
    markdown_content: str
