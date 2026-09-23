import os
import sys
import json
import base64
from pathlib import Path
sys.path.insert(0, ".")

def get_audio_info(path):
    if not os.path.exists(path):
        return 0.0, ""
    try:
        import wave
        with wave.open(path, 'rb') as w:
            dur = w.getnframes() / float(w.getframerate())
    except Exception:
        # Fallback estimation for MP3 / raw audio
        dur = max(3.0, os.path.getsize(path) / 16000.0)
    with open(path, 'rb') as af:
        b64 = base64.b64encode(af.read()).decode('utf-8')
    return dur, b64

def rebuild():
    output_dir = "outputs_v3/kebo107"
    with open(f"{output_dir}/teaching_units.json", "r", encoding="utf-8") as f:
        units = json.load(f)
        
    # Sort units strictly by order
    units.sort(key=lambda x: x.get("order", 0))
    
    slides_data = []
    total_time = 0.0
    
    for i, u in enumerate(units):
        u_id = u["unit_id"]
        aud_path = f"{output_dir}/audio/{u_id}.wav"
        dur, aud_b64 = get_audio_info(aud_path)
        
        # Clean title
        raw_title = u.get("learning_goal", f"Slide {i+1}")
        if " - " in raw_title:
            clean_title = raw_title.split(" - ")[-1].strip()
        elif ": " in raw_title:
            clean_title = raw_title.split(": ")[-1].strip()
        elif " & " in raw_title and len(raw_title) > 40:
            clean_title = raw_title.split(" & ")[0].strip()
        else:
            clean_title = raw_title
            
        words = clean_title.split()
        if len(words) > 7:
            clean_title = " ".join(words[:7])
            
        slide_entry = {
            "index": i + 1,
            "unit_id": u_id,
            "title": clean_title,
            "bullets": u.get("bullet_sentences", []),
            "duration": round(dur, 2),
            "start_time": round(total_time, 2),
            "end_time": round(total_time + dur, 2),
            "audio_b64": f"data:audio/wav;base64,{aud_b64}" if aud_b64 else ""
        }
        slides_data.append(slide_entry)
        print(f"Slide {i+1} [{u_id[:8]}]: '{clean_title}' | Start: {total_time:.1f}s | Duration: {dur:.1f}s | End: {total_time+dur:.1f}s")
        total_time += dur
        
    from app.infrastructure.presentation.html_deck_builder import HtmlDeckBuilder
    html_path = HtmlDeckBuilder.build(output_dir)
    print("Rebuilt presentation.html successfully at:", html_path)
    return slides_data, total_time

if __name__ == "__main__":
    rebuild()
