from typing import Any
from app.domain.models.understanding import Understanding
from app.domain.models.lesson_plan import LessonPlan, Lesson
from app.infrastructure.ai.agents.base_agent import BaseAgent
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.prompts.loader import PromptLoader

class LessonPlannerAgent(BaseAgent):
    """Generates a structured lesson plan."""

    def __init__(self, provider: LLMProvider | None = None, prompt_loader: PromptLoader | None = None) -> None:
        super().__init__(provider=provider, prompt_loader=prompt_loader)

    async def run(self, understanding: Understanding) -> LessonPlan:
        import json
        import asyncio
        
        # ADVANCED BATCHED PRESERVATION GUARD
        # To guarantee high-quality AI generated objectives for 94+ subtopics without LLM truncation,
        # we process the subtopics in small batches of 15 and merge the results.
        batch_size = 15
        subtopics = understanding.subtopics
        subtopic_batches = [subtopics[i:i + batch_size] for i in range(0, len(subtopics), batch_size)]
        
        schema = LessonPlan.model_json_schema() if hasattr(LessonPlan, "model_json_schema") else LessonPlan.schema()
        semaphore = asyncio.Semaphore(2)
        
        def extract_fuzzy_key(data_dict, possible_keys, default_val=None):
            if not isinstance(data_dict, dict): return default_val
            for pk in possible_keys:
                for k in data_dict.keys():
                    if pk.lower() == k.lower():
                        return data_dict[k]
            for k in data_dict.keys():
                for pk in possible_keys:
                    if pk.lower() in k.lower().replace("_", "").replace(" ", ""):
                        return data_dict[k]
            return default_val
            
        def validate_result(res):
            if isinstance(res, list):
                if len(res) > 0 and isinstance(res[0], dict) and extract_fuzzy_key(res[0], ["title", "objective", "minutes", "sequence"]):
                    res = {"lessons": res}
                elif len(res) > 0 and isinstance(res[0], dict):
                    res = res[0]
                else:
                    raise ValueError("Output is an array but not an array of objects.")
            if not isinstance(res, dict):
                raise ValueError(f"Expected dict but got {type(res)}")
                
            lessons_arr = extract_fuzzy_key(res, ["lessons", "lessonplan", "lessonlist", "units"])
            if not lessons_arr:
                if "error" in res:
                    raise ValueError(f"AI refused to generate with error: {res['error']}")
                extracted_list = []
                for val in res.values():
                    if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and extract_fuzzy_key(val[0], ["title", "objective"]):
                        extracted_list = val
                        break
                if extracted_list:
                    res["lessons"] = extracted_list
                else:
                    raise ValueError(f"LLM failed to generate any lessons. Keys found: {list(res.keys())}")
            else:
                res["lessons"] = lessons_arr
            return res
            
        def safe_int(val, default=10):
            if isinstance(val, int): return val
            if isinstance(val, float): return int(val)
            if isinstance(val, str):
                import re
                digits = re.search(r'\d+', val)
                if digits:
                    return int(digits.group())
            return default
            
        async def process_batch(batch):
            async with semaphore:
                context = {
                    "chapter_title": understanding.chapter_title,
                    "main_topic": understanding.main_topic,
                    "major_topics": understanding.major_topics,
                    "subtopics": json.dumps(batch, indent=2),
                    "learning_objectives": understanding.learning_objectives,
                    "understanding_json": "" 
                }
                try:
                    result_dict = await self.generate_structured("lesson_planner", schema=schema, context=context, validator=validate_result)
                    return result_dict.get("lessons", [])
                except Exception as e:
                    self.logger.warning(f"Lesson batch generation failed: {e}. Falling back to programmatic.")
                    fallback = []
                    for sub in batch:
                        fallback.append({"title": sub, "objective": f"Detailed understanding of {sub}", "estimated_minutes": 5})
                    return fallback

        tasks = [process_batch(b) for b in subtopic_batches]
        results = await asyncio.gather(*tasks)
        
        all_lessons_data = []
        for res in results:
            if isinstance(res, list):
                all_lessons_data.extend(res)
                
        lessons = []
        for i, l in enumerate(all_lessons_data):
            lessons.append(Lesson(
                sequence=i+1,
                title=extract_fuzzy_key(l, ["title", "name", "heading"], f"Lesson {i+1}"),
                objective=extract_fuzzy_key(l, ["objective", "goal", "learning"], "Objective"),
                estimated_minutes=safe_int(extract_fuzzy_key(l, ["minutes", "time", "duration", "estimated"], 5))
            ))
            
        return LessonPlan(
            document_id=getattr(understanding, 'document_id', "unknown"),
            lessons=lessons
        )
