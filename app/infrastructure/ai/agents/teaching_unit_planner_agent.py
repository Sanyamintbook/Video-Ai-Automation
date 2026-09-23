import uuid
from typing import Any
from app.domain.models.understanding import Understanding
from app.domain.models.lesson_plan import LessonPlan
from app.domain.models.teaching_unit import TeachingUnit
from app.infrastructure.ai.agents.base_agent import BaseAgent
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.prompts.loader import PromptLoader

class TeachingUnitPlannerAgent(BaseAgent):
    """Generates granular teaching units."""

    def __init__(self, provider: LLMProvider | None = None, prompt_loader: PromptLoader | None = None) -> None:
        super().__init__(provider=provider, prompt_loader=prompt_loader)

    async def run(
        self,
        understanding: Understanding,
        faiss_dir: str,
        coverage_mode: str = "Full Auto-Extract (100% Quality)"
    ) -> list[TeachingUnit]:
        from app.infrastructure.rag.vector_store import LocalVectorStore
        
        # Load local vector store for RAG grounding
        vector_store = LocalVectorStore()
        try:
            vector_store.load(faiss_dir)
            has_faiss = True
        except Exception as e:
            self.logger.warning(f"Failed to load FAISS index from {faiss_dir}: {e}. Slide generation will lack source context.")
            has_faiss = False
            
        units = []
        
        # Determine the target subtopics based on coverage_mode
        all_subtopics = understanding.subtopics or [understanding.main_topic]
        
        if "Concise Summary" in coverage_mode or "4-6" in coverage_mode:
            target_slide_count = 4  # 4 content slides + 1 outro = 5 slides total
            chunk_step = max(1, len(all_subtopics) // target_slide_count)
            clustered = []
            for i in range(0, len(all_subtopics), chunk_step):
                group = all_subtopics[i:i + chunk_step]
                if group:
                    if len(group) > 1:
                        clustered.append(f"{group[0]} & {group[1]}")
                    else:
                        clustered.append(group[0])
                if len(clustered) >= target_slide_count:
                    break
            working_subtopics = clustered[:target_slide_count]
            self.logger.info(f"Concise Mode: Clustered {len(all_subtopics)} detailed subtopics into {len(working_subtopics)} summary slides.")
        elif "Standard Lesson" in coverage_mode or "8-15" in coverage_mode:
            target_slide_count = 10  # 10 content slides + 1 outro = 11 slides total
            chunk_step = max(1, len(all_subtopics) // target_slide_count)
            clustered = []
            for i in range(0, len(all_subtopics), chunk_step):
                group = all_subtopics[i:i + chunk_step]
                if group:
                    if len(group) > 1:
                        clustered.append(f"{group[0]} & {group[1]}")
                    else:
                        clustered.append(group[0])
                if len(clustered) >= target_slide_count:
                    break
            working_subtopics = clustered[:target_slide_count]
            self.logger.info(f"Standard Mode: Clustered {len(all_subtopics)} subtopics into {len(working_subtopics)} lesson slides.")
        else:
            working_subtopics = all_subtopics
            self.logger.info(f"Full Quality Mode: Generating individual slides for all {len(working_subtopics)} subtopics.")

        # Define the schema for a batch of units
        schema = {
            "type": "object",
            "properties": {
                "units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "learning_goal": {"type": "string"},
                            "bullet_sentences": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "source_refs": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["learning_goal", "bullet_sentences"]
                    }
                }
            },
            "required": ["units"]
        }
        
        def extract_fuzzy_key(data_dict, possible_keys, default_val=None):
            if not isinstance(data_dict, dict): return default_val
            for k in data_dict.keys():
                for pk in possible_keys:
                    if pk.lower() in k.lower().replace("_", "").replace(" ", ""):
                        return data_dict[k]
            return default_val
            
        def validate_batch(res):
            if isinstance(res, list):
                if len(res) > 0 and isinstance(res[0], dict):
                    res = {"units": res}
                else:
                    raise ValueError("Output is an array but not an array of objects.")
            if not isinstance(res, dict):
                raise ValueError(f"Expected dict but got {type(res)}")
                
            if "units" in res and isinstance(res["units"], list) and len(res["units"]) == 0:
                raise ValueError("The AI returned an empty 'units' array.")
                
            if "units" not in res:
                if extract_fuzzy_key(res, ["learninggoal", "title"]) and extract_fuzzy_key(res, ["bulletsentences", "bullet", "points"]):
                    res = {"units": [res]}
                else:
                    extracted_list = []
                    for val in res.values():
                        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and extract_fuzzy_key(val[0], ["learninggoal", "title"]):
                            extracted_list = val
                            break
                    if extracted_list:
                        res = {"units": extracted_list}
                    else:
                        dict_list = [v for v in res.values() if isinstance(v, dict) and extract_fuzzy_key(v, ["learninggoal", "title"])]
                        if dict_list:
                            res = {"units": dict_list}
                        else:
                            raise ValueError("Missing 'units' array in generated JSON.")
            return res
                
        import asyncio
        import json
        
        semaphore = asyncio.Semaphore(1)
        batch_size = 5
        
        # Slice working subtopics into batches of 5
        subtopic_batches = [working_subtopics[i:i + batch_size] for i in range(0, len(working_subtopics), batch_size)]
        
        async def generate_batch(batch_idx, subtopics_batch):
            async with semaphore:
                batch_query = f"{understanding.main_topic} " + " ".join(subtopics_batch)
                retrieved_context = ""
                if has_faiss:
                    try:
                        chunks = vector_store.similarity_search(batch_query, top_k=8)
                        retrieved_context = "\n\n".join(chunks)
                    except Exception as e:
                        self.logger.warning(f"FAISS retrieval failed for batch {batch_idx+1}: {e}")
                
                context = {
                    "subtopics_json": json.dumps(subtopics_batch),
                    "batch_size": len(subtopics_batch),
                    "main_topic": understanding.main_topic,
                    "definitions": understanding.definitions,
                    "examples": understanding.examples,
                    "raw_text": retrieved_context
                }
                
                try:
                    self.logger.info(f"Generating slide BATCH {batch_idx+1}/{len(subtopic_batches)} (Contains {len(subtopics_batch)} slides)...")
                    result_dict = await self.generate_structured(
                        "teaching_unit_planner", 
                        schema=schema, 
                        context=context, 
                        validator=validate_batch
                    )
                    
                    batch_units = []
                    generated_units = result_dict.get("units", [])
                    
                    for j, u_data in enumerate(generated_units):
                        bullets = extract_fuzzy_key(u_data, ["bulletsentences", "bullet", "points", "sentences"], [])
                        if len(bullets) > 6:
                            bullets = bullets[:6]
                        while len(bullets) < 3:
                            if bullets:
                                bullets.append(bullets[-1])
                            else:
                                bullets.append("Detailed analysis of this topic.")
                                
                        refs = extract_fuzzy_key(u_data, ["sourcerefs", "source", "refs", "references"], [])
                        if not refs:
                            refs = ["Textbook Material"]
                                
                        unit = TeachingUnit(
                            unit_id=str(uuid.uuid4()),
                            lesson_id=understanding.main_topic,
                            order=(batch_idx * batch_size) + j + 1,
                            learning_goal=extract_fuzzy_key(u_data, ["learninggoal", "title", "heading", "goal"], "Goal"),
                            bullet_sentences=bullets,
                            source_refs=refs
                        )
                        batch_units.append(unit)
                        
                    return batch_units
                except Exception as e:
                    self.logger.warning(f"Failed to generate slide batch {batch_idx+1}: {e}. Using programmatic synthesis.")
                    fallback_units = []
                    for j, sub_title in enumerate(subtopics_batch):
                        unit = TeachingUnit(
                            unit_id=str(uuid.uuid4()),
                            lesson_id=understanding.main_topic,
                            order=(batch_idx * batch_size) + j + 1,
                            learning_goal=f"{understanding.main_topic} - {sub_title}",
                            bullet_sentences=[
                                f"Overview of {sub_title}.",
                                f"Key concepts regarding {sub_title}.",
                                "Refer to the textbook material for further details."
                            ],
                            source_refs=["Programmatic Fallback"]
                        )
                        fallback_units.append(unit)
                    return fallback_units
                    
        tasks = [generate_batch(i, batch) for i, batch in enumerate(subtopic_batches)]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            if res is not None and isinstance(res, list):
                units.extend(res)
                
        for i, u in enumerate(units):
            u.order = i + 2  # Shift everything by +1 since intro is order=1

        # 1. Generate Intro Slide
        intro_unit = TeachingUnit(
            unit_id=str(uuid.uuid4()),
            lesson_id=understanding.main_topic,
            order=1,
            learning_goal=understanding.chapter_title,
            bullet_sentences=[understanding.main_topic],
            source_refs=["System Generated Intro"]
        )
        
        # 2. Generate Summary Slide
        summary_unit = TeachingUnit(
            unit_id=str(uuid.uuid4()),
            lesson_id=understanding.main_topic,
            order=len(units) + 2,
            learning_goal="Summary",
            bullet_sentences=[
                f"Key takeaways for {understanding.chapter_title}:"
            ] + [t.split('&')[0].strip() for t in working_subtopics[:3]],
            source_refs=["System Generated Summary"]
        )
        
        # 3. Generate Thank You Slide
        thank_you_unit = TeachingUnit(
            unit_id=str(uuid.uuid4()),
            lesson_id=understanding.main_topic,
            order=len(units) + 3,
            learning_goal="Thank You!",
            bullet_sentences=[],
            source_refs=["System Generated Outro"]
        )
        
        return [intro_unit] + units + [summary_unit, thank_you_unit]
