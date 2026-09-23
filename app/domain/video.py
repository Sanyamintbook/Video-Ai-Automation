from pydantic import BaseModel

class Video(BaseModel):
    document_id: str
    storage_path: str
    duration_sec: float
