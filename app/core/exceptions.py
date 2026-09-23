"""Project-wide custom exceptions."""


class OlympiadException(Exception):
    """Base exception."""


class InvalidFileException(OlympiadException):
    """Unsupported file uploaded."""


class AgentException(OlympiadException):
    """AI Agent failed to execute or format output."""


class AgentException(OlympiadException):
    """AI Agent failed to execute or format output."""


class AgentException(OlympiadException):
    """AI Agent failed to execute or format output."""


class AgentException(OlympiadException):
    """AI Agent failed to execute or format output."""


class ContentExtractionException(OlympiadException):
    """Content extraction failed."""


class AIProviderException(OlympiadException):
    """LLM provider failed."""


class ProviderAuthenticationException(AIProviderException):
    """Provider authentication failed."""


class ProviderTimeoutException(AIProviderException):
    """Provider request timed out."""


class ProviderResponseException(AIProviderException):
    """Provider returned an invalid response."""


class LessonPlanningException(OlympiadException):
    """Lesson planning failed."""


class TeachingUnitException(OlympiadException):
    """Teaching unit generation failed."""


class ValidationException(OlympiadException):
    """Validation failed."""


class SlideGenerationException(OlympiadException):
    """Slide generation failed."""


class VoiceGenerationException(OlympiadException):
    """Voice generation failed."""


class RenderingException(OlympiadException):
    """Video rendering failed."""