from pydantic import BaseModel, Field

class Lesson(BaseModel):
    sequence: int
    title: str
    objective: str
    estimated_minutes: int

class LessonPlan(BaseModel):
    document_id: str
    lessons: list[Lesson] = Field(default_factory=list)
