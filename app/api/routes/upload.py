import os
import uuid
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path

from app.config.settings import get_settings
from app.infrastructure.queue.tasks import run_full_pipeline, update_job_status

router = APIRouter()

@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # We removed the strict pre-upload health check because we now use a load-balanced 
        # multi-server setup. If the primary server is down, the background task will 
        # automatically rotate to the fallback server during generation.
            
        settings = get_settings()
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        safe_name = "".join(c for c in file.filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
        name_without_ext = os.path.splitext(safe_name)[0]
        # Keep a short hash just in case of duplicate uploads
        document_id = f"{name_without_ext}_{uuid.uuid4().hex[:4]}"
        
        upload_dir = Path(settings.upload_directory) / document_id
        os.makedirs(upload_dir, exist_ok=True)
        file_path = upload_dir / safe_name
        
        # Use a fresh, clean output directory 
        output_dir = Path(settings.upload_directory).parent / "outputs_v3" / document_id
        os.makedirs(output_dir, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        update_job_status(
            job_id=job_id,
            status="PENDING",
            stage="parsing",
            units_done=0,
            units_total=0,
            document_id=document_id
        )
        
        # Start async pipeline chain in the background
        background_tasks.add_task(
            run_full_pipeline, 
            job_id, 
            document_id, 
            str(file_path), 
            str(output_dir)
        )
        
        return {
            "job_id": job_id,
            "document_id": document_id
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"UPLOAD ERROR: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(e)}", "traceback": error_trace}
        )
