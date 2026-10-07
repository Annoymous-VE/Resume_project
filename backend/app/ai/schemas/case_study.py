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

class ClientBrochureMetric(BaseModel):
    label: str = Field(..., description="Short metric label, e.g. 'Processing Speedup' or 'Operational Cost'")
    value: str = Field(..., description="Stat or quantified figure, e.g. '65% Faster' or '3x Scale'")
    description: str = Field(..., description="Brief one-line business explanation")

class GeneratedClientBrochure(BaseModel):
    project_id: str
    title: str = Field(..., description="Compelling, client-ready headline/solution title")
    tagline: str = Field(..., description="Punchy one-sentence value proposition")
    executive_summary: str = Field(..., description="Client-facing overview describing business challenge and triumph")
    target_audience: Optional[str] = Field(None, description="Primary industry or business stakeholders benefiting from this solution")
    key_metrics: List[ClientBrochureMetric] = Field(default_factory=list, description="Top 2-4 quantifiable business ROI metrics")
    sections: List[CaseStudySection] = Field(default_factory=list)
    markdown_content: str

