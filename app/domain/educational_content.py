from pydantic import BaseModel
from typing import Literal

class SourceDocument(BaseModel):
    document_id: str
    filename: str
    content_type: Literal["pdf", "docx", "pptx", "txt", "md"]
    raw_text: str
    storage_path: str
