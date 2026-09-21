from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from app.ai.schemas.knowledge import CoverageLevel

class QuestionTarget(BaseModel):
    area: str
    rationale: str
    expected_gain: float = 1.0

class GeneratedQuestion(BaseModel):
    id: str
    target_area: str
    question: str
    rationale: str
    context_hook: Optional[str] = None

class InitialQuestionsResult(BaseModel):
    questions: List[GeneratedQuestion] = Field(default_factory=list)

class FollowUpQuestionResult(BaseModel):
    has_next_question: bool
    question: Optional[GeneratedQuestion] = None
    stop_reason: Optional[str] = None
    coverage_update: Dict[str, CoverageLevel] = Field(default_factory=dict)
