from pydantic import BaseModel

class Definition(BaseModel):
    term: str
    meaning: str

class Understanding(BaseModel):
    document_id: str
    chapter_title: str
    main_topic: str
    major_topics: list[str]
    subtopics: list[str]
    learning_objectives: list[str]
    definitions: list[Definition]
    examples: list[str]
    summary: str
