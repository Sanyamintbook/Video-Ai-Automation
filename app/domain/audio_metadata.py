from pydantic import BaseModel

class AudioClip(BaseModel):
    unit_id: str
    storage_path: str
    duration_sec: float
