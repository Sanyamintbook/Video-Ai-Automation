from pydantic import BaseModel


class TimelineEntry(BaseModel):
    unit_id: str
    slide_start_sec: float
    slide_end_sec: float
    audio_path: str


class Timeline(BaseModel):
    entries: list[TimelineEntry]
