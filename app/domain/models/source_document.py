from typing import Literal
from pydantic import BaseModel, Field

class SourceDocument(BaseModel):
    document_id: str
    filename: str
    content_type: Literal["pdf", "docx", "pptx", "txt", "md"]
    raw_text: str = Field(min_length=1)
    storage_path: str
