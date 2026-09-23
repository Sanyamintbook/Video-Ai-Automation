from pydantic import BaseModel, Field

class Slide(BaseModel):
    unit_id: str
    title: str
    bullets: list[str] = Field(default_factory=list)
    image_ref: str | None = None
    speaker_notes: str = ""
