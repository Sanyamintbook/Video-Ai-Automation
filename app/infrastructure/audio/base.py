from abc import ABC, abstractmethod

class TTSProvider(ABC):
    """
    Abstract base class for all Text-to-Speech (TTS) providers.
    """
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text into raw audio bytes (e.g., MP3 format).
        """
        raise NotImplementedError
