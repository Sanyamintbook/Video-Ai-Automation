"""Shared enums for domain and workflow states."""

from enum import Enum


class ContentType(str, Enum):
    BOOK = "book"
    CHAPTER = "chapter"
    TOPIC = "topic"
    SUBTOPIC = "subtopic"
    PARAGRAPH = "paragraph"


class AIProvider(str, Enum):
    GEMINI = "gemini"
    OLLAMA = "ollama"


class JobStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class TeachingUnitStatus(str, Enum):
    CREATED = "created"
    SCRIPT_GENERATED = "script_generated"
    VALIDATED = "validated"
    SLIDE_GENERATED = "slide_generated"
    AUDIO_GENERATED = "audio_generated"
    COMPLETED = "completed"