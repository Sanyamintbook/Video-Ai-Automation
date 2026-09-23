from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class Job(BaseModel):
    job_id: str
    document_id: str
    status: Literal["PENDING", "RUNNING", "DONE", "FAILED"]
    stage: str
    units_total: int
    units_done: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    failure_reason: str | None = None
