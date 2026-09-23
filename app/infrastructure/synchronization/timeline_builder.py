from typing import List
from app.domain.models.audio_clip import AudioClip
from app.domain.models.timeline import TimelineEntry

class TimelineBuilder:
    """
    Pure mathematical deterministic builder that computes exact slide-display windows 
    based on cumulative audio durations.
    """
    
    @staticmethod
    def build(audio_clips: List[AudioClip]) -> List[TimelineEntry]:
        timeline = []
        current_time = 0.0
        
        for clip in audio_clips:
            # We assume audio_clips is already ordered correctly
            slide_start = current_time
            slide_end = current_time + clip.duration_sec
            
            entry = TimelineEntry(
                unit_id=clip.unit_id,
                slide_start_sec=slide_start,
                slide_end_sec=slide_end,
                audio_path=clip.storage_path
            )
            timeline.append(entry)
            
            # The next slide starts exactly when this one ends
            current_time = slide_end
            
        return timeline
