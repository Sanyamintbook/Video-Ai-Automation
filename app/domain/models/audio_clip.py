from pydantic import BaseModel, Field

class AudioClip(BaseModel):
    unit_id: str = Field(description="Foreign key referencing the TeachingUnit")
    storage_path: str = Field(description="Storage path of the synthesized audio file")
    duration_sec: float = Field(gt=0, description="Real measured duration of the audio clip in seconds")
