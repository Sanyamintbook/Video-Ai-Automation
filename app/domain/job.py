from pydantic import BaseModel
from typing import Literal

class Job(BaseModel):
    job_id: str
    document_id: str
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
    progress: int = 0
    failed_units: list[str] = []
    error_message: str | None = None
