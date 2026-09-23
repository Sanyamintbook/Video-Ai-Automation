import pytest

from app.domain.models.audio_clip import AudioClip
from app.infrastructure.synchronization.timeline_builder import TimelineBuilder

def test_timeline_builder_contiguity_and_sum():
    """
    Test Case 7 & 10: TimelineBuilder output is contiguous (no gaps/overlaps).
    Sum of all TimelineEntry durations equals sum of all AudioClip durations exactly.
    """
    clips = [
        AudioClip(unit_id="u1", storage_path="1.mp3", duration_sec=14.87, format="mp3", sample_rate=24000),
        AudioClip(unit_id="u2", storage_path="2.mp3", duration_sec=12.43, format="mp3", sample_rate=24000),
        AudioClip(unit_id="u3", storage_path="3.mp3", duration_sec=9.1, format="mp3", sample_rate=24000)
    ]
    
    timeline = TimelineBuilder.build(clips)
    
    assert len(timeline) == 3
    
    # Check start of first
    assert timeline[0].slide_start_sec == 0.0
    
    # Check contiguity
    for i in range(len(timeline) - 1):
        # The end of one slide MUST exactly equal the start of the next slide
        assert abs(timeline[i].slide_end_sec - timeline[i+1].slide_start_sec) < 1e-9
        
    # Check total sum invariant
    total_timeline_duration = sum(entry.slide_end_sec - entry.slide_start_sec for entry in timeline)
    total_clips_duration = sum(clip.duration_sec for clip in clips)
    
    assert abs(total_timeline_duration - total_clips_duration) < 1e-9

def test_timeline_builder_single_unit():
    """
    Test Case 7: Single-unit document (edge case).
    TimelineBuilder produces exactly one TimelineEntry starting at 0.0.
    """
    clips = [
        AudioClip(unit_id="u1", storage_path="1.mp3", duration_sec=5.5, format="mp3", sample_rate=24000)
    ]
    timeline = TimelineBuilder.build(clips)
    
    assert len(timeline) == 1
    assert timeline[0].slide_start_sec == 0.0
    assert timeline[0].slide_end_sec == 5.5
