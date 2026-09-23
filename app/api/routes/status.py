import json
import os
from fastapi import APIRouter, HTTPException
from app.infrastructure.state.local_store import get_job_state, STATE_FILE

router = APIRouter()

@router.get("/jobs/{identifier}/status")
async def get_job_status(identifier: str):
    # Determine the job_id. It might be passed directly as a job_id,
    # or it might be passed as a document_id which we'd have to find.
    
    data = get_job_state(identifier)
    
    if not data:
        from app.infrastructure.state.sqlite_store import find_job_by_document
        data = find_job_by_document(identifier)
                
    if not data:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    try:
        units_done = data.get("units_done", 0)
        units_total = data.get("units_total", 0)
        
        percent_complete = 0
        if units_total > 0:
            percent_complete = int((units_done / units_total) * 100)
        elif data.get("status") == "DONE":
            percent_complete = 100
            
        return {
            "job_id": identifier if data.get("job_id") is None else data.get("job_id", identifier), # fallback if job_id missing inside data
            "document_id": data.get("document_id"),
            "status": data.get("status"),
            "stage": data.get("stage"),
            "units_total": units_total,
            "units_done": units_done,
            "percent_complete": percent_complete,
            "failure_reason": data.get("failure_reason")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read job state: {str(e)}")
