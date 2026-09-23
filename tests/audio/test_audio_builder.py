import os
import base64
import shutil
import pytest
from unittest.mock import MagicMock
from app.infrastructure.audio.audio_builder import AudioBuilder
from app.infrastructure.audio.base import TTSProvider
from app.domain.models.narration_segment import NarrationSegment
from app.core.exceptions import VoiceGenerationException

import io
import wave

def get_silent_wav_bytes(duration_sec=3.5, rate=44100):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * duration_sec))
    return buf.getvalue()

@pytest.fixture
def temp_output_dir(tmp_path):
    output_dir = tmp_path / "outputs"
    os.makedirs(output_dir, exist_ok=True)
    yield str(output_dir)
    shutil.rmtree(output_dir, ignore_errors=True)

def test_audio_builder_success(temp_output_dir):
    mock_provider = MagicMock(spec=TTSProvider)
    mock_provider.synthesize.return_value = get_silent_wav_bytes(3.5)

    segment = NarrationSegment(
        unit_id="unit-1234",
        narration_text="Hello students, this is a short test of the audio builder component.",
        estimated_duration_sec=3.5,
        validation_status="PASS",
        validation_notes=[]
    )

    builder = AudioBuilder(provider=mock_provider)
    clip = builder.synthesize(segment, temp_output_dir)

    assert clip.unit_id == "unit-1234"
    assert clip.duration_sec > 0
    assert os.path.exists(clip.storage_path)
    assert os.path.getsize(clip.storage_path) > 0
    
    # Wave duration check
    with wave.open(clip.storage_path, "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
    assert abs(clip.duration_sec - duration) < 0.01

def test_audio_builder_empty_narration(temp_output_dir):
    builder = AudioBuilder()
    segment = NarrationSegment.model_construct(
        unit_id="unit-123",
        narration_text="",
        estimated_duration_sec=0.0
    )
    with pytest.raises(VoiceGenerationException) as excinfo:
        builder.synthesize(segment, temp_output_dir)
    assert "empty narration text" in str(excinfo.value)

def test_audio_builder_corrupt_mp3(temp_output_dir):
    mock_provider = MagicMock(spec=TTSProvider)
    # Return invalid MP3 bytes
    mock_provider.synthesize.return_value = b"completely-invalid-audio-headers"

    segment = NarrationSegment(
        unit_id="unit-567",
        narration_text="This is a test of a corrupted audio file failure logic.",
        estimated_duration_sec=4.0
    )

    builder = AudioBuilder(provider=mock_provider)
    with pytest.raises(VoiceGenerationException) as excinfo:
        builder.synthesize(segment, temp_output_dir)
    assert "corrupt audio output" in str(excinfo.value) or "Failed to read MP3 duration" in str(excinfo.value)
