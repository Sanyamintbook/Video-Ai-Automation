from typing import Any
from app.domain.models.source_document import SourceDocument
from app.domain.models.understanding import Understanding
from app.infrastructure.ai.agents.base_agent import BaseAgent
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.prompts.loader import PromptLoader

class ContentUnderstandingAgent(BaseAgent):
    """Extracts structured understanding from educational content."""

    def __init__(self, provider: LLMProvider | None = None, prompt_loader: PromptLoader | None = None) -> None:
        super().__init__(provider=provider, prompt_loader=prompt_loader)

    async def run(self, content: SourceDocument) -> Understanding:
        import asyncio
        source_text = content.raw_text
        
        # --- PHASE 1: MAP-REDUCE GRANULAR SUBTOPIC EXTRACTION ---
        # Instead of skipping the middle of the document, we chunk the ENTIRE document 
        # into 6500 character segments (approx 2-3 pages) and extract granular subtopics from each chunk sequentially.
        # This prevents the LLM from over-summarizing while avoiding GPU VRAM thrashing.
        chunk_size = 6500
        overlap = 500
        chunks = []
        start = 0
        while start < len(source_text):
            chunks.append(source_text[start:start + chunk_size])
            start += chunk_size - overlap
            
        self.logger.info(f"Chunked massive document into {len(chunks)} segments for deep granular subtopic extraction.")
        
        all_subtopics = []
        
        async def extract_subtopics(idx, chunk_text):
            try:
                self.logger.info(f"Extracting subtopics from chunk {idx+1}/{len(chunks)}...")
                result = await self.generate_structured(
                    "subtopic_extraction",
                    schema={"type": "object", "properties": {"subtopics": {"type": "array", "items": {"type": "string"}}}, "required": ["subtopics"]},
                    context={"content": chunk_text},
                    validator=lambda r: r if isinstance(r, dict) and "subtopics" in r else {"subtopics": []}
                )
                return result.get("subtopics", [])
            except Exception as e:
                self.logger.warning(f"Failed to extract subtopics from chunk {idx+1}: {e}")
                return []
                
        # Run subtopic extraction sequentially (Semaphore=1) to prevent Ollama GPU VRAM overflow & CPU RAM swapping
        semaphore = asyncio.Semaphore(1)
        async def sem_extract(idx, chunk_text):
            async with semaphore:
                return await extract_subtopics(idx, chunk_text)
                
        extraction_tasks = [sem_extract(i, chunk) for i, chunk in enumerate(chunks)]
        extracted_results = await asyncio.gather(*extraction_tasks)
        
        for res in extracted_results:
            if isinstance(res, list):
                # Deduplicate while preserving order
                for sub in res:
                    if sub not in all_subtopics:
                        all_subtopics.append(sub)
                        
        self.logger.info(f"Successfully extracted {len(all_subtopics)} highly granular subtopics across the entire document.")
        
        # --- PHASE 2: HIGH-LEVEL CHAPTER UNDERSTANDING ---
        # We still need the main title, summary, etc. We use the first chunk for this.
        # But we will overwrite the 'subtopics' it generates with our massive aggregated list.
        first_chunk = chunks[0] if chunks else source_text
        
        context = {
            "content": first_chunk,
        }
        
        schema = Understanding.model_json_schema() if hasattr(Understanding, "model_json_schema") else Understanding.schema()
        
        def extract_fuzzy_key(data_dict, possible_keys, default_val=None):
            if not isinstance(data_dict, dict): return default_val
            for k in data_dict.keys():
                for pk in possible_keys:
                    if pk.lower() in k.lower().replace("_", "").replace(" ", ""):
                        return data_dict[k]
            return default_val

        def validate_dict(res):
            if isinstance(res, list):
                if len(res) > 0 and isinstance(res[0], dict):
                    res = res[0]
                else:
                    raise ValueError("Output is a list and does not contain a dictionary.")
            if not isinstance(res, dict):
                raise ValueError(f"Expected dict but got {type(res)}")
            if "error" in res:
                raise ValueError(f"AI failed format with error: {res['error']}")
            return res
            
        result_dict = await self.generate_structured(
            "content_understanding", 
            schema=schema, 
            context=context,
            validator=validate_dict
        )
        
        # Ensure we always return something that parses into Understanding
        chapter_title = extract_fuzzy_key(result_dict, ["chaptertitle", "title", "heading"])
        main_topic = extract_fuzzy_key(result_dict, ["maintopic", "topic", "subject"])
        subtopics = extract_fuzzy_key(result_dict, ["subtopics", "subtopic", "sections"])
        
        # Override with our deeply extracted Map-Reduce subtopics
        if all_subtopics:
            subtopics = all_subtopics
        
        if not chapter_title or not main_topic or not subtopics:
            raise ValueError(f"LLM returned incomplete JSON. Got: {result_dict}")
            
        return Understanding(
            document_id=content.document_id,
            chapter_title=chapter_title,
            main_topic=main_topic,
            major_topics=extract_fuzzy_key(result_dict, ["majortopics", "major", "concepts"], ["General Topic"]),
            subtopics=subtopics,
            learning_objectives=extract_fuzzy_key(result_dict, ["learningobjectives", "objectives", "goals"], ["Understand the material"]),
            definitions=extract_fuzzy_key(result_dict, ["definitions", "terms"], []),
            examples=extract_fuzzy_key(result_dict, ["examples", "cases"], []),
            summary=extract_fuzzy_key(result_dict, ["summary", "overview"], "Summary not available.")
        )
