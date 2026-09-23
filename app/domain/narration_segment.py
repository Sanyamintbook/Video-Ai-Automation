from pydantic import BaseModel

class NarrationSegment(BaseModel):
    unit_id: str
    narration_text: str
    estimated_duration_sec: float
    validation_status: str = "PENDING"
    validation_notes: list[str] = []
