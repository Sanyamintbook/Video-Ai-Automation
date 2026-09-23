import asyncio
import os
from pathlib import Path
import fitz

from app.core.enums import ContentType
from app.domain.models.educational_content import EducationalContent
from app.infrastructure.ai.agents.content_understanding_agent import ContentUnderstandingAgent
from app.infrastructure.ai.agents.lesson_planner_agent import LessonPlannerAgent
from app.infrastructure.ai.agents.teaching_unit_planner_agent import TeachingUnitPlannerAgent
from app.infrastructure.presentation.pptx_builder import PptxBuilder

async def main():
    # Load a sample PDF if any exists, else just make dummy text
    print("Starting test...")
    text = "This is a sample educational text about Photosynthesis."
    edu_content = EducationalContent(
        title="test.pdf",
        content_type=ContentType.CHAPTER,
        raw_content=text,
        extracted_content=text,
    )
    print("Content parsed, running ContentUnderstandingAgent...")
    understanding_agent = ContentUnderstandingAgent()
    understanding = await understanding_agent.run(edu_content)
    print("Understanding output:", understanding)
    
    print("Running LessonPlannerAgent...")
    lesson_planner = LessonPlannerAgent()
    lesson_plan = await lesson_planner.run(understanding)
    print("Lesson Plan output:", lesson_plan)
    
if __name__ == "__main__":
    asyncio.run(main())
