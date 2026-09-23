from pydantic import BaseModel

# Comprehensive polyfill for Pydantic V1/V2 cross-compatibility
if not hasattr(BaseModel, "model_dump"):
    BaseModel.model_dump = lambda self, *args, **kwargs: self.dict(*args, **kwargs)

if not hasattr(BaseModel, "model_dump_json"):
    BaseModel.model_dump_json = lambda self, *args, **kwargs: self.json(*args, **kwargs)

if not hasattr(BaseModel, "model_validate"):
    @classmethod
    def _model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, cls):
            return obj
        return cls.parse_obj(obj)
    BaseModel.model_validate = _model_validate

if not hasattr(BaseModel, "model_validate_json"):
    @classmethod
    def _model_validate_json(cls, json_data, *args, **kwargs):
        return cls.parse_raw(json_data)
    BaseModel.model_validate_json = _model_validate_json

if not hasattr(BaseModel, "model_json_schema"):
    @classmethod
    def _model_json_schema(cls, *args, **kwargs):
        return cls.schema(*args, **kwargs)
    BaseModel.model_json_schema = _model_json_schema


from app.domain.models.source_document import SourceDocument
from app.domain.models.understanding import Understanding
from app.domain.models.lesson_plan import LessonPlan, Lesson
from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.slide import Slide
from app.domain.models.audio_metadata import AudioMetadata
from app.domain.models.timeline import Timeline
from app.domain.models.job import Job
from app.domain.models.narration_segment import NarrationSegment
from app.domain.models.audio_clip import AudioClip
from app.domain.models.video import Video
