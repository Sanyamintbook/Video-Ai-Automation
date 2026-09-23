import os
import json
import asyncio
from datetime import datetime
from loguru import logger
from typing import Optional, Dict, Any

from app.config.settings import get_settings
from app.infrastructure.ingestion.pdf_parser import PdfParser
from app.infrastructure.ai.agents.content_understanding_agent import ContentUnderstandingAgent
from app.infrastructure.ai.agents.lesson_planner_agent import LessonPlannerAgent
from app.infrastructure.ai.agents.teaching_unit_planner_agent import TeachingUnitPlannerAgent
from app.infrastructure.ai.agents.script_generator_agent import ScriptGeneratorAgent
from app.infrastructure.validation.schema_validator import SchemaValidator
from app.domain.models.understanding import Understanding
from app.domain.models.lesson_plan import LessonPlan
from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.narration_segment import NarrationSegment
from app.domain.models.slide import Slide
from app.domain.models.audio_clip import AudioClip
from app.infrastructure.audio.audio_builder import AudioBuilder
from app.infrastructure.presentation.pptx_builder import PptxBuilder
from app.core.exceptions import AgentException, VoiceGenerationException
from app.infrastructure.state.sqlite_store import save_job, get_job


def update_job_status(
    job_id: str,
    status: str,
    stage: str,
    units_done: int = -1,
    units_total: int = -1,
    units_failed: int = -1,
    failure_reason: str = None,
    document_id: str = None,
    output_dir: str = None,
    options: Dict[str, Any] = None
):
    data = {
        "status": status,
        "stage": stage,
        "updated_at": datetime.now().isoformat()
    }
    if document_id:
        data["document_id"] = document_id
    if output_dir:
        data["output_dir"] = output_dir
    if options:
        data["options"] = options
    if units_done >= 0:
        data["units_done"] = units_done
    if units_total >= 0:
        data["units_total"] = units_total
    if units_failed >= 0:
        data["units_failed"] = units_failed
    if failure_reason:
        data["failure_reason"] = failure_reason
    if status in ("DONE", "FAILED"):
        data["completed_at"] = datetime.now().isoformat()
        
    save_job(job_id, data)


# Pipeline functions with Checkpoint Resilience

async def parse_document_task(job_id: str, document_id: str, file_path: str, output_dir: str, options: dict = None):
    logger.info(f"[{job_id}] Starting parse_document_task")
    if os.path.exists(os.path.join(output_dir, "edu_content.json")) and os.path.exists(os.path.join(output_dir, "faiss_index")):
        logger.info(f"[{job_id}] Skipping parse_document_task: Output already exists.")
        return {"status": "SUCCESS", "document_id": document_id}
        
    update_job_status(job_id, "RUNNING", "parsing", document_id=document_id, output_dir=output_dir, options=options)
    try:
        parser = PdfParser()
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        edu_content = parser.parse(file_bytes, os.path.basename(file_path))
        
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "parsed_text.txt"), "w", encoding="utf-8") as f:
            f.write(edu_content.raw_text)
        
        with open(os.path.join(output_dir, "edu_content.json"), "w", encoding="utf-8") as f:
            f.write(edu_content.model_dump_json(indent=2))
            
        logger.info(f"[{job_id}] Chunking and indexing document text with FAISS")
        from app.infrastructure.rag.text_splitter import RecursiveCharacterTextSplitter
        from app.infrastructure.rag.vector_store import LocalVectorStore
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_text(edu_content.raw_text)
        
        if chunks:
            vector_store = LocalVectorStore()
            vector_store.add_documents(chunks)
            faiss_dir = os.path.join(output_dir, "faiss_index")
            vector_store.save(faiss_dir)
            logger.info(f"[{job_id}] Successfully built and saved FAISS index with {len(chunks)} chunks.")
            
        return {"status": "SUCCESS", "document_id": document_id}
    except Exception as e:
        logger.exception(f"[{job_id}] Parsing failed")
        update_job_status(job_id, "FAILED", "parsing", failure_reason=f"Failed to parse document: {str(e)}")
        raise


async def understand_content_task(job_id: str, document_id: str, output_dir: str):
    logger.info(f"[{job_id}] Starting understand_content_task")
    if os.path.exists(os.path.join(output_dir, "understanding.json")):
        logger.info(f"[{job_id}] Skipping understand_content_task: Output already exists.")
        return {"status": "SUCCESS"}
        
    update_job_status(job_id, "RUNNING", "understanding")
    try:
        with open(os.path.join(output_dir, "edu_content.json"), "r", encoding="utf-8") as f:
            content_dict = json.load(f)
        from app.domain.models.source_document import SourceDocument
        edu_content = SourceDocument(**content_dict)
        
        understanding_agent = ContentUnderstandingAgent()
        understanding = await understanding_agent.run(edu_content)
        
        validator = SchemaValidator()
        val_res = validator.validate(understanding, Understanding)
        if not val_res.is_valid:
            raise AgentException(f"ContentUnderstanding validation failed: {', '.join(val_res.errors)}")
            
        with open(os.path.join(output_dir, "understanding.json"), "w", encoding="utf-8") as f:
            f.write(understanding.model_dump_json(indent=2))
            
        return {"status": "SUCCESS"}
    except Exception as e:
        logger.exception(f"[{job_id}] Understanding failed")
        update_job_status(job_id, "FAILED", "understanding", failure_reason=f"Content Understanding failed: {str(e)}")
        raise


async def plan_lesson_task(job_id: str, document_id: str, output_dir: str):
    logger.info(f"[{job_id}] Starting plan_lesson_task")
    if os.path.exists(os.path.join(output_dir, "lesson_plan.json")):
        logger.info(f"[{job_id}] Skipping plan_lesson_task: Output already exists.")
        return {"status": "SUCCESS"}
        
    update_job_status(job_id, "RUNNING", "lesson_planning")
    try:
        with open(os.path.join(output_dir, "understanding.json"), "r", encoding="utf-8") as f:
            und_dict = json.load(f)
        understanding = Understanding(**und_dict)
        
        lesson_planner = LessonPlannerAgent()
        lesson_plan = await lesson_planner.run(understanding)
        
        validator = SchemaValidator()
        val_res = validator.validate(lesson_plan, LessonPlan)
        if not val_res.is_valid:
            raise AgentException(f"LessonPlan validation failed: {', '.join(val_res.errors)}")
            
        with open(os.path.join(output_dir, "lesson_plan.json"), "w", encoding="utf-8") as f:
            f.write(lesson_plan.model_dump_json(indent=2))
            
        return {"status": "SUCCESS"}
    except Exception as e:
        logger.exception(f"[{job_id}] Lesson planning failed")
        update_job_status(job_id, "FAILED", "lesson_planning", failure_reason=f"Lesson Planning failed: {str(e)}")
        raise


async def generate_units_task(job_id: str, document_id: str, output_dir: str, options: dict = None):
    logger.info(f"[{job_id}] Starting generate_units_task")
    if os.path.exists(os.path.join(output_dir, "teaching_units.json")):
        logger.info(f"[{job_id}] Skipping generate_units_task: Output already exists.")
        with open(os.path.join(output_dir, "teaching_units.json"), "r", encoding="utf-8") as f:
            units = json.load(f)
        update_job_status(job_id, "RUNNING", "unit_planning", units_done=0, units_total=len(units))
        return {"status": "SUCCESS", "units_count": len(units)}
        
    update_job_status(job_id, "RUNNING", "unit_planning")
    try:
        with open(os.path.join(output_dir, "understanding.json"), "r", encoding="utf-8") as f:
            und_dict = json.load(f)
        understanding = Understanding(**und_dict)
        
        faiss_dir = os.path.join(output_dir, "faiss_index")
        coverage_mode = (options or {}).get("coverage_mode", "Full Auto-Extract (100% Quality)")
            
        unit_planner = TeachingUnitPlannerAgent()
        units = await unit_planner.run(understanding, faiss_dir, coverage_mode=coverage_mode)
        
        validator = SchemaValidator()
        val_res = validator.validate(units, TeachingUnit)
        if not val_res.is_valid:
            raise AgentException(f"TeachingUnits validation failed: {', '.join(val_res.errors)}")
            
        units_dict = [unit.model_dump() for unit in units]
        with open(os.path.join(output_dir, "teaching_units.json"), "w", encoding="utf-8") as f:
            json.dump(units_dict, f, indent=2)
            
        update_job_status(job_id, "RUNNING", "unit_planning", units_done=0, units_total=len(units))
        return {"status": "SUCCESS", "units_count": len(units)}
    except Exception as e:
        logger.exception(f"[{job_id}] Unit planning failed")
        update_job_status(job_id, "FAILED", "unit_planning", failure_reason=f"Unit Planning failed: {str(e)}")
        raise


async def generate_narration_for_unit_task(job_id: str, unit_dict: dict, output_dir: str):
    unit_id = unit_dict["unit_id"]
    try:
        success_path = os.path.join(output_dir, f"narration_{unit_id}.json")
        if os.path.exists(success_path):
            return {"status": "SUCCESS", "unit_id": unit_id}
            
        unit = TeachingUnit(**unit_dict)
        query = f"{unit.learning_goal} " + " ".join(unit.bullet_sentences or [])
        
        source_context = ""
        faiss_dir = os.path.join(output_dir, "faiss_index")
        if os.path.exists(faiss_dir):
            try:
                from app.infrastructure.rag.vector_store import LocalVectorStore
                vector_store = LocalVectorStore()
                vector_store.load(faiss_dir)
                retrieved_chunks = await asyncio.to_thread(vector_store.similarity_search, query, top_k=3)
                if retrieved_chunks:
                    source_context = "\n\n".join(retrieved_chunks)
            except Exception as ex:
                logger.warning(f"[{job_id}] FAISS retrieval warning for unit {unit_id}: {str(ex)}")

        script_generator = ScriptGeneratorAgent()
        segment = await script_generator.run(unit, source_context=source_context)
        
        with open(os.path.join(output_dir, f"narration_{unit_id}.json"), "w", encoding="utf-8") as f:
            f.write(segment.model_dump_json(indent=2))
            
        return {"status": "SUCCESS", "unit_id": unit_id}
    except Exception as e:
        logger.error(f"[{job_id}] Narration failed for unit {unit_id}. Error: {str(e)}")
        fail_data = {"error": f"Narration generation failed: {str(e)}"}
        with open(os.path.join(output_dir, f"failure_narration_{unit_id}.json"), "w", encoding="utf-8") as f:
            json.dump(fail_data, f)
        return {"status": "FAILED", "unit_id": unit_id}


def synthesize_audio_for_unit_task(job_id: str, unit_id: str, output_dir: str, voice: str = "af_heart", speed: float = 1.0):
    try:
        success_path = os.path.join(output_dir, f"audio_clip_{unit_id}.json")
        if os.path.exists(success_path):
            return {"status": "SUCCESS", "unit_id": unit_id}
            
        narration_path = os.path.join(output_dir, f"narration_{unit_id}.json")
        if not os.path.exists(narration_path):
            raise VoiceGenerationException("Skipped audio synthesis because narration script is missing.")
            
        with open(narration_path, "r", encoding="utf-8") as f:
            seg_dict = json.load(f)
        segment = NarrationSegment(**seg_dict)
        
        builder = AudioBuilder(voice=voice, speed=speed)
        clip = builder.synthesize(segment, output_dir)
        
        with open(os.path.join(output_dir, f"audio_clip_{unit_id}.json"), "w", encoding="utf-8") as f:
            f.write(clip.model_dump_json(indent=2))
            
        return {"status": "SUCCESS", "unit_id": unit_id}
    except Exception as e:
        fail_data = {"error": str(e)}
        with open(os.path.join(output_dir, f"failure_audio_{unit_id}.json"), "w", encoding="utf-8") as f:
            json.dump(fail_data, f)
        return {"status": "FAILED", "unit_id": unit_id}


def build_slide_for_unit_task(job_id: str, unit_dict: dict, output_dir: str):
    unit_id = unit_dict["unit_id"]
    try:
        success_path = os.path.join(output_dir, f"slide_{unit_id}.json")
        if os.path.exists(success_path):
            return {"status": "SUCCESS", "unit_id": unit_id}
            
        narration_path = os.path.join(output_dir, f"narration_{unit_id}.json")
        speaker_notes = ""
        if os.path.exists(narration_path):
            with open(narration_path, "r", encoding="utf-8") as f:
                seg = json.load(f)
            speaker_notes = seg.get("narration_text", "")
            
        slide = Slide(
            unit_id=unit_id,
            title=unit_dict["learning_goal"],
            bullets=unit_dict["bullet_sentences"],
            speaker_notes=speaker_notes
        )
        
        with open(os.path.join(output_dir, f"slide_{unit_id}.json"), "w", encoding="utf-8") as f:
            f.write(slide.model_dump_json(indent=2))
            
        return {"status": "SUCCESS", "unit_id": unit_id}
    except Exception as e:
        logger.error(f"[{job_id}] Slide build failed for unit {unit_id}: {str(e)}")
        return {"status": "FAILED", "unit_id": unit_id}


async def trigger_unit_parallelism_task(job_id: str, document_id: str, output_dir: str, options: dict = None):
    opts = options or {}
    voice = opts.get("voice", "af_heart")
    speed = float(opts.get("speed", 1.0))
    
    logger.info(f"[{job_id}] Processing unit scripts and audio (Voice: {voice}, Speed: {speed})...")
    update_job_status(job_id, "RUNNING", "audio_synthesis")
    try:
        with open(os.path.join(output_dir, "teaching_units.json"), "r", encoding="utf-8") as f:
            units_list = json.load(f)
            
        if not units_list:
            await finalize_pipeline_task(job_id, document_id, output_dir, options)
            return {"status": "SUCCESS", "message": "No units to process."}
            
        total_units = len(units_list)
        units_done = 0
        
        media_queue = asyncio.Queue()
        consumer_workers_count = min(4, (os.cpu_count() or 2))
        
        async def media_consumer_worker(worker_id: int):
            nonlocal units_done
            while True:
                try:
                    unit_dict = await media_queue.get()
                except asyncio.CancelledError:
                    break
                if unit_dict is None:
                    media_queue.task_done()
                    break
                unit_id = unit_dict["unit_id"]
                try:
                    await asyncio.to_thread(synthesize_audio_for_unit_task, job_id, unit_id, output_dir, voice, speed)
                    await asyncio.to_thread(build_slide_for_unit_task, job_id, unit_dict, output_dir)
                except Exception as ex:
                    logger.error(f"[Worker-{worker_id}] Error in media generation for {unit_id}: {ex}")
                finally:
                    units_done += 1
                    update_job_status(job_id, "RUNNING", "audio_synthesis", units_done=units_done, units_total=total_units)
                    media_queue.task_done()
                    
        consumers = [asyncio.create_task(media_consumer_worker(i + 1)) for i in range(consumer_workers_count)]
        
        # Script generation
        script_semaphore = asyncio.Semaphore(1)
        
        async def produce_script(unit_dict):
            async with script_semaphore:
                unit_id = unit_dict["unit_id"]
                await generate_narration_for_unit_task(job_id, unit_dict, output_dir)
                await media_queue.put(unit_dict)
                    
        producer_tasks = [asyncio.create_task(produce_script(u)) for u in units_list]
        await asyncio.gather(*producer_tasks)
                
        for _ in range(consumer_workers_count):
            await media_queue.put(None)
            
        await media_queue.join()
        for c in consumers:
            c.cancel()
            
        await finalize_pipeline_task(job_id, document_id, output_dir, options)
        return {"status": "SUCCESS", "queued_units": len(units_list)}
    except Exception as e:
        logger.exception(f"[{job_id}] Unit execution failed")
        update_job_status(job_id, "FAILED", "audio_synthesis", failure_reason=f"Execution failed: {str(e)}")
        raise


async def finalize_pipeline_task(job_id: str, document_id: str, output_dir: str, options: dict = None):
    logger.info(f"[{job_id}] [Step 6/6] Finalizing presentation and rendering video...")
    opts = options or {}
    try:
        with open(os.path.join(output_dir, "teaching_units.json"), "r", encoding="utf-8") as f:
            units_list = json.load(f)
        units_list.sort(key=lambda x: x.get("order", 0))
            
        slides = []
        narration_segments = []
        audio_clips = []
        
        for unit_dict in units_list:
            unit_id = unit_dict["unit_id"]
            
            slide_path = os.path.join(output_dir, f"slide_{unit_id}.json")
            if os.path.exists(slide_path):
                with open(slide_path, "r", encoding="utf-8") as f:
                    slide_dict = json.load(f)
                slides.append(Slide(**slide_dict))
                
            narration_path = os.path.join(output_dir, f"narration_{unit_id}.json")
            if os.path.exists(narration_path):
                with open(narration_path, "r", encoding="utf-8") as f:
                    seg_dict = json.load(f)
                narration_segments.append(NarrationSegment(**seg_dict))
                
            clip_path = os.path.join(output_dir, f"audio_clip_{unit_id}.json")
            if os.path.exists(clip_path):
                with open(clip_path, "r", encoding="utf-8") as f:
                    clip_dict = json.load(f)
                audio_clips.append(AudioClip(**clip_dict))

        # Save metadata files
        with open(os.path.join(output_dir, "script.json"), "w", encoding="utf-8") as f:
            json.dump({"document_id": document_id, "segments": [s.model_dump() for s in narration_segments]}, f, indent=2)

        with open(os.path.join(output_dir, "audio_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"document_id": document_id, "clips": [c.model_dump() for c in audio_clips]}, f, indent=2)

        valid_units = [TeachingUnit(**u) for u in units_list]
        
        # Build PowerPoint with custom styling parameters
        template_path = opts.get("template_path")
        title_color = opts.get("title_color", "#FFFFFF")
        body_color = opts.get("body_color", "#FFFFFF")
        accent_color = opts.get("accent_color", "#14B8A6")
        bg_color = opts.get("bg_color", "#0B3436")
        
        builder = PptxBuilder()
        slides_models, presentation_path = builder.build(
            units=valid_units,
            narration_segments=narration_segments,
            output_dir=output_dir,
            template_path=template_path,
            title_color=title_color,
            body_color=body_color,
            accent_color=accent_color,
            bg_color=bg_color
        )
        logger.info(f"[{job_id}] Presentation built successfully at {presentation_path}")
        
        # Build standalone HTML5 presentation deck
        from app.infrastructure.presentation.html_deck_builder import HtmlDeckBuilder
        try:
            HtmlDeckBuilder.build(
                output_dir=output_dir,
                title_color=title_color,
                body_color=body_color,
                accent_color=accent_color,
                bg_color=bg_color
            )
        except Exception as he:
            logger.warning(f"[{job_id}] HTML Deck Builder warning: {he}")

        # Build timeline and render video
        from app.infrastructure.synchronization.timeline_builder import TimelineBuilder
        timeline = TimelineBuilder.build(audio_clips)
        timeline_path = os.path.join(output_dir, "timeline.json")
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump([t.model_dump() for t in timeline], f, indent=2)
            
        if presentation_path and timeline:
            from app.infrastructure.video.video_renderer import VideoRenderer
            try:
                video_output_path = os.path.join(output_dir, "video.mp4")
                resolution = opts.get("resolution", "1080p")
                logger.info(f"[{job_id}] Starting video rendering ({resolution})...")
                VideoRenderer.render(document_id, presentation_path, timeline, video_output_path, resolution=resolution)
                logger.info(f"[{job_id}] Video built successfully at {video_output_path}")
            except Exception as ve:
                logger.error(f"[{job_id}] Video rendering failed: {str(ve)}")

        total_units = len(units_list)
        update_job_status(job_id, "DONE", "completed", units_done=total_units, units_total=total_units, units_failed=0)
        logger.info(f"[{job_id}] Pipeline completed successfully.")
        return {"status": "SUCCESS", "pptx_path": presentation_path}
    except Exception as e:
        logger.exception(f"[{job_id}] Finalization failed")
        update_job_status(job_id, "FAILED", "completed", failure_reason=f"Finalization failed: {str(e)}")
        raise


# Coordinator for the whole pipeline
async def run_full_pipeline(job_id: str, document_id: str, file_path: str, output_dir: str, options: dict = None):
    """Executes the pipeline sequentially with checkpointing and parameter options."""
    try:
        logger.info(f"========== PIPELINE STARTED FOR JOB {job_id} ==========")
        
        logger.info(f"[{job_id}] [Step 1/6] Parsing Document & FAISS Embeddings")
        await parse_document_task(job_id, document_id, file_path, output_dir, options)
        
        logger.info(f"[{job_id}] [Step 2/6] AI Content Understanding")
        await understand_content_task(job_id, document_id, output_dir)
        
        logger.info(f"[{job_id}] [Step 3/6] AI Lesson Planning")
        await plan_lesson_task(job_id, document_id, output_dir)
        
        logger.info(f"[{job_id}] [Step 4/6] AI Unit Generation")
        await generate_units_task(job_id, document_id, output_dir, options)
        
        logger.info(f"[{job_id}] [Step 5/6] Unit Processing - Generating Slides, Scripts, and Audio...")
        await trigger_unit_parallelism_task(job_id, document_id, output_dir, options)
        
        logger.info(f"========== PIPELINE FINISHED FOR JOB {job_id} ==========")
    except Exception as e:
        logger.error(f"[{job_id}] Pipeline aborted due to error: {e}")
