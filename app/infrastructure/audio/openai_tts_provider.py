from openai import OpenAI
from loguru import logger
from app.config.settings import get_settings
from app.core.exceptions import ProviderAuthenticationException, AIProviderException
from app.infrastructure.audio.base import TTSProvider

class OpenAITTSProvider(TTSProvider):
    """
    OpenAI TTS API implementation with graceful gTTS fallback if credentials are missing or call fails.
    """
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.voice = settings.tts_voice
        self.model = "tts-1"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def synthesize(self, text: str) -> bytes:
        # Check if text contains Devanagari characters (Hindi)
        is_hindi = any(ord(char) in range(0x0900, 0x0980) for char in text)
        lang = "hi" if is_hindi else "en"
        
        if not self.client:
            logger.info(f"OpenAI API key not configured. Falling back to free gTTS synthesis (language: {lang}).")
            try:
                from gtts import gTTS
                import io
                fp = io.BytesIO()
                tts = gTTS(text=text, lang=lang)
                tts.write_to_fp(fp)
                return fp.getvalue()
            except Exception as gtts_err:
                raise ProviderAuthenticationException(f"OpenAI key missing, and gTTS fallback failed: {str(gtts_err)}")
        
        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
            return response.content
        except Exception as e:
            logger.warning(f"OpenAI TTS synthesis failed: {str(e)}. Attempting gTTS fallback (language: {lang}).")
            try:
                from gtts import gTTS
                import io
                fp = io.BytesIO()
                tts = gTTS(text=text, lang=lang)
                tts.write_to_fp(fp)
                return fp.getvalue()
            except Exception as gtts_err:
                raise AIProviderException(f"Both OpenAI TTS and gTTS fallback failed. OpenAI error: {str(e)}, gTTS error: {str(gtts_err)}") from e
