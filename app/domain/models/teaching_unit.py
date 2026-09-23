from pydantic import BaseModel, Field

class TeachingUnit(BaseModel):
    unit_id: str
    lesson_id: str
    order: int
    learning_goal: str
    bullet_sentences: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
