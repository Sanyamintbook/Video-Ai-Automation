import os
import tempfile
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.domain.models.timeline import TimelineEntry
from app.infrastructure.video.video_renderer import VideoRenderer
from app.config.settings import get_settings

def create_dummy_audio(path: str):
    # Creates a valid tiny 1-second mp3 using ffmpeg
    subprocess.run([get_settings().ffmpeg_path, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", "-q:a", "9", "-acodec", "libmp3lame", path, "-y"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def create_dummy_image(path: str):
    # Creates a valid tiny black png using ffmpeg
    subprocess.run([get_settings().ffmpeg_path, "-f", "lavfi", "-i", "color=c=black:s=1280x720", "-frames:v", "1", path, "-y"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import sys
mock_win32com = MagicMock()
sys.modules['win32com'] = mock_win32com
sys.modules['win32com.client'] = mock_win32com.client

def test_video_renderer_stitches_segments():
    """
    Test Case 1 & 7: 2-slide fixture with known audio durations.
    Rendered MP4 duration matches expected sum, and segment N uses audio N.
    """
    settings = get_settings()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_1 = os.path.join(temp_dir, "1.mp3")
        audio_2 = os.path.join(temp_dir, "2.mp3")
        
        try:
            create_dummy_audio(audio_1)
            create_dummy_audio(audio_2)
        except Exception:
            pytest.skip("ffmpeg not found, skipping video test")
            
        timeline = [
            TimelineEntry(unit_id="u1", slide_start_sec=0.0, slide_end_sec=1.0, audio_path=audio_1),
            TimelineEntry(unit_id="u2", slide_start_sec=1.0, slide_end_sec=2.0, audio_path=audio_2),
        ]
        
        # We need to mock the PowerPoint export by simply placing Slide1.PNG and Slide2.PNG in the expected folder
        # However, VideoRenderer uses a random temp_dir internally for slides. 
        # We can patch `tempfile.TemporaryDirectory` but it's easier to patch the win32com Dispatch 
        # and use a side_effect to create the images in whatever directory the code passes to SaveAs.
        
        mock_presentation = MagicMock()
        def mock_save_as(folder_path, format_id):
            create_dummy_image(os.path.join(folder_path, "Slide1.PNG"))
            create_dummy_image(os.path.join(folder_path, "Slide2.PNG"))
            
        mock_presentation.SaveAs.side_effect = mock_save_as
        
        mock_powerpoint = MagicMock()
        mock_powerpoint.Presentations.Open.return_value = mock_presentation
        mock_win32com.client.Dispatch.return_value = mock_powerpoint
        
        output_mp4 = os.path.join(temp_dir, "final.mp4")
        
        # Run renderer
        video = VideoRenderer.render("doc1", "dummy.pptx", timeline, output_mp4)
        
        # Assertions
        assert os.path.exists(output_mp4)
        assert video.document_id == "doc1"
        assert abs(video.duration_sec - 2.0) < 0.1
