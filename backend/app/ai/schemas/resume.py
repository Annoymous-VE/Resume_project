from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DocumentBlock(BaseModel):
    id: str
    type: str = Field(..., description="heading, bullet, paragraph, or key_value")
    text: str
    order: int
    page: int = 1
    column: int = 1
    level: Optional[int] = None
    bbox: Optional[List[float]] = None

class DocumentMetadata(BaseModel):
    filename: str
    file_type: str
    total_pages: int = 1
    file_size_bytes: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)

class DocumentRepresentation(BaseModel):
    metadata: DocumentMetadata
    blocks: List[DocumentBlock] = Field(default_factory=list)
