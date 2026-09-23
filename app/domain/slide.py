from pydantic import BaseModel

class Slide(BaseModel):
    unit_id: str
    title: str
    bullets: list[str]
    image_ref: str | None = None
    speaker_notes: str
