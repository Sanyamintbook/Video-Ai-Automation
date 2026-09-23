from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.enums import ContentType


class EducationalContent(BaseModel):
    """
    Raw educational content uploaded by the user.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))

    title: str

    content_type: ContentType

    language: str = "en"

    source_file: str | None = None

    raw_content: str

    extracted_content: str

    created_at: datetime = Field(default_factory=datetime.utcnow)

    metadata: dict = Field(default_factory=dict)