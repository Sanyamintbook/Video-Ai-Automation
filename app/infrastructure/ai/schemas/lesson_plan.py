from pydantic import BaseModel, Field


class LessonStep(BaseModel):
    sequence: int = Field(ge=1)
    title: str
    objective: str
    estimated_minutes: int = Field(gt=0)


class LessonPlanOutput(BaseModel):
    lesson_title: str
    estimated_total_duration: int = Field(gt=0)
    lessons: list[LessonStep]
    learning_objectives: list[str] = Field(default_factory=list)
    learning_sequence: list[str] = Field(default_factory=list)
