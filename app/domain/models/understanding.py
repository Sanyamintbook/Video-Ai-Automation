from pydantic import BaseModel, Field

class Understanding(BaseModel):
    document_id: str
    chapter_title: str
    main_topic: str
    major_topics: list[str] = Field(default_factory=list)
    subtopics: list[str] = Field(
        default_factory=list,
        description="Strictly a list of single nouns or short entities representing distinct syllabus topics (e.g., 'Iron', 'Solar Energy'). MUST NOT contain full sentences, facts, or descriptions."
    )
    learning_objectives: list[str] = Field(default_factory=list)
    definitions: list[dict] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    summary: str = ""
