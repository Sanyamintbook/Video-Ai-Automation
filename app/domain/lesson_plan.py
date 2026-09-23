from pydantic import BaseModel

class Lesson(BaseModel):
    id: str
    objective: str
    order: int
    duration: int

class LessonPlan(BaseModel):
    document_id: str
    lessons: list[Lesson]
