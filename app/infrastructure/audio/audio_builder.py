import os
import wave
from app.core.exceptions import VoiceGenerationException
from app.domain.models.audio_clip import AudioClip
from app.domain.models.narration_segment import NarrationSegment
from app.infrastructure.audio.base import TTSProvider
from app.infrastructure.audio.kokoro_tts_provider import KokoroTTSProvider


class AudioBuilder:
    """
    Synthesizes narration text using a TTSProvider (Kokoro v1.0 / gTTS) and measures real duration
    from the output audio file.
    """
    def __init__(self, provider: TTSProvider | None = None, voice: str = "af_heart", speed: float = 1.0) -> None:
        self.provider = provider or KokoroTTSProvider(voice=voice, speed=speed)

    def synthesize(self, segment: NarrationSegment, output_dir: str) -> AudioClip:
        if not segment.narration_text:
            raise VoiceGenerationException(f"Cannot synthesize empty narration text for unit {segment.unit_id}")

        audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        file_path = os.path.join(audio_dir, f"{segment.unit_id}.wav")

        try:
            audio_bytes = self.provider.synthesize(segment.narration_text)
            
            if not audio_bytes or len(audio_bytes) == 0:
                raise VoiceGenerationException(f"Received empty audio bytes from TTS provider for unit {segment.unit_id}")

            with open(file_path, "wb") as f:
                f.write(audio_bytes)

            if os.path.getsize(file_path) == 0:
                raise VoiceGenerationException(f"Generated audio file is 0 bytes for unit {segment.unit_id}")

            duration = 0.0
            # Try wave module first
            try:
                with wave.open(file_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
            except Exception:
                # Try mutagen for mp3/wav fallback
                try:
                    from mutagen import File as MutagenFile
                    audio = MutagenFile(file_path)
                    if audio and audio.info:
                        duration = audio.info.length
                except Exception:
                    # Heuristic fallback based on word count
                    word_count = len(segment.narration_text.split())
                    duration = max(3.0, word_count / 2.5)

            if duration <= 0:
                duration = 3.0

            return AudioClip(
                unit_id=segment.unit_id,
                storage_path=file_path,
                duration_sec=round(duration, 2)
            )

        except Exception as e:
            if not isinstance(e, VoiceGenerationException):
                raise VoiceGenerationException(f"Audio synthesis failed for unit {segment.unit_id}: {str(e)}") from e
            raise
