import os
import json
import base64
from pathlib import Path
from typing import List, Dict

def sanitize_title(title: str, max_words: int = 7) -> str:
    """Ensures slide titles are punchy, readable, and never collide with content."""
    if not title:
        return "Lesson Overview"
    title = title.replace("\n", " ").strip()
    if " - " in title:
        parts = title.split(" - ")
        title = parts[-1].strip()
    elif ": " in title:
        parts = title.split(": ")
        title = parts[-1].strip()
    elif " & " in title and len(title) > 40:
        parts = title.split(" & ")
        title = parts[0].strip()
        
    words = title.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]).title()
    return title.title()


def get_audio_info(path):
    if not os.path.exists(path):
        return 0.0, ""
    try:
        import wave
        with wave.open(path, 'rb') as w:
            dur = w.getnframes() / float(w.getframerate())
    except Exception:
        dur = max(3.0, os.path.getsize(path) / 16000.0)
    with open(path, 'rb') as af:
        b64 = base64.b64encode(af.read()).decode('utf-8')
    return dur, b64


class HtmlDeckBuilder:
    """
    Builds an automated, continuous, fully-synchronized Educational AI Video Player.
    Features:
    - 100% strict sequential slide ordering (Slide 1 -> Slide 2 -> Slide 3 -> Slide 4 -> Slide 5)
    - Full continuous video timeline scrubber (0:00 to Total Duration)
    - Auto-advancing slide transitions synchronized with neural voice narration
    - Official Mintbook template vector aesthetics (teal arc, cyan arc, logo, VYDIA branding)
    - Client-side MP4/WebM video export recorder
    """
    
    @staticmethod
    def build(
        output_dir: str,
        title_color: str = "#FFFFFF",
        body_color: str = "#E2E8F0",
        accent_color: str = "#14B8A6",
        bg_color: str = "#083335"
    ) -> str:
        doc_dir = Path(output_dir)
        units_file = doc_dir / "teaching_units.json"
        audio_dir = doc_dir / "audio"
        
        # Load units strictly in order
        units = []
        if units_file.exists():
            try:
                with open(units_file, "r", encoding="utf-8") as uf:
                    units = json.load(uf)
                units.sort(key=lambda x: x.get("order", 0))
            except Exception:
                pass
                
        # Load Mintbook logo
        logo_path = Path(__file__).resolve().parent / "assets" / "mintbook_logo.png"
        logo_b64 = ""
        if logo_path.exists():
            with open(logo_path, "rb") as lf:
                logo_b64 = base64.b64encode(lf.read()).decode("utf-8")
                
        slides_data = []
        total_time = 0.0
        
        for i, u in enumerate(units):
            u_id = u.get("unit_id", "")
            aud_file = str(audio_dir / f"{u_id}.wav")
            dur, aud_b64 = get_audio_info(aud_file)
            
            raw_title = u.get("learning_goal", f"Slide {i+1}")
            clean_title = sanitize_title(raw_title)
            
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
            total_time += dur
            
        if not slides_data:
            return ""
            
        logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="height: 28px; object-fit: contain;" alt="Mintbook"/>' if logo_b64 else '<span style="color:#083335; font-weight:800; font-size:1.1rem;">mintbook</span>'
            
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mintbook AI Video Player</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; }}
        body {{ background: #030712; color: #FFFFFF; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 12px; }}
        
        .video-player-card {{
            width: 100%;
            max-width: 1120px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        
        /* 16:9 HD Video Screen */
        .video-screen {{ 
            width: 100%; 
            aspect-ratio: 16 / 9; 
            background: #083335; 
            border-radius: 14px; 
            box-shadow: 0 30px 70px rgba(0,0,0,0.7); 
            position: relative; 
            overflow: hidden; 
            display: flex; 
            flex-direction: column; 
            border: 1px solid rgba(255,255,255,0.08); 
            cursor: pointer;
            container-type: size;
        }}
        
        /* Official Mintbook Vector Arcs */
        .circle-tr {{
            position: absolute;
            top: -18%;
            right: -8%;
            width: 38cqw;
            height: 38cqw;
            background: #028090;
            border-radius: 50%;
            pointer-events: none;
            z-index: 1;
        }}
        
        .circle-br {{
            position: absolute;
            bottom: -16%;
            right: -6%;
            width: 25cqw;
            height: 25cqw;
            background: #00A896;
            border-radius: 50%;
            pointer-events: none;
            z-index: 1;
        }}
        
        .mintbook-logo-card {{
            position: absolute;
            top: 2.5cqw;
            right: 3.5cqw;
            background: #FFFFFF;
            padding: 0.8cqw 1.8cqw;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        
        .mintbook-logo-card img {{
            height: 2.5cqw !important;
        }}
        
        /* Slide Content Area */
        .slide-content-area {{
            position: relative;
            z-index: 3;
            flex: 1;
            padding: 4.5cqw 5cqw;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            max-width: 70cqw;
        }}
        
        .slide-title-text {{
            font-size: 3.5cqw;
            font-weight: 700;
            color: #FFFFFF;
            line-height: 1.25;
            transition: all 0.3s ease;
        }}
        
        .slide-title-text.centered-title {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 4.5cqw;
            text-align: center;
            width: 80cqw;
            margin: 0;
            max-width: none;
        }}
        
        .title-divider-line {{
            width: 40cqw;
            height: 2px;
            background-color: rgba(255,255,255,0.1);
            margin-top: 1.5cqw;
            position: relative;
        }}
        
        .title-divider-line::after {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 15cqw;
            background-color: {accent_color};
        }}
        
        .bullets-container {{
            margin-top: 2.5cqw;
            display: flex;
            flex-direction: column;
            gap: 1.5cqw;
            z-index: 10;
        }}
        
        .bullet-point {{
            font-size: 2.2cqw;
            line-height: 1.5;
            color: #E2E8F0;
            display: flex;
            align-items: flex-start;
            gap: 1.5cqw;
        }}
        
        .bullet-point::before {{
            content: "•";
            color: {accent_color};
            font-size: 2.8cqw;
            line-height: 1.1;
        }}
        
        .vydia-branding {{
            position: absolute;
            bottom: 24px;
            left: 36px;
            display: flex;
            flex-direction: column;
            gap: 2px;
            z-index: 5;
        }}
        
        .dots-row {{
            display: flex;
            gap: 6px;
            margin-bottom: 4px;
        }}
        
        .dot {{ width: 8px; height: 8px; border-radius: 50%; }}
        .dot-1 {{ background: #02C39A; }}
        .dot-2 {{ background: #00A896; }}
        
        .vydia-text {{
            color: #6FA9A6;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 1.5px;
        }}
        
        .mintbook-product-text {{
            color: #6FA9A6;
            font-size: 0.75rem;
            font-style: italic;
        }}
        
        /* Bottom Right Slide Number */
        .slide-counter-number {{
            position: absolute;
            bottom: 24px;
            right: 36px;
            font-size: 1.2rem;
            font-weight: 700;
            color: #FFFFFF;
            z-index: 5;
        }}
        
        /* Slide Content Area */
        .slide-content-area {{
            position: relative;
            z-index: 3;
            flex: 1;
            padding: 48px 56px 40px 56px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            max-width: 64%;
        }}
        
        .slide-title-text {{
            font-size: 2.75rem;
            font-weight: 700;
            color: #FFFFFF;
            line-height: 1.25;
            text-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        
        .title-divider-line {{
            width: 320px;
            height: 1px;
            background: rgba(0, 168, 150, 0.45);
            margin: 14px 0 22px 0;
        }}
        
        .bullets-container {{
            list-style-type: none;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        
        .bullet-point {{
            font-size: 1.75rem;
            line-height: 1.65;
            color: #E2E8F0;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}
        
        .bullet-point::before {{
            content: "•";
            color: #00A896;
            font-size: 1.6rem;
            line-height: 1;
            font-weight: bold;
        }}
        
        /* Center Play Overlay */
        .play-overlay {{
            position: absolute;
            inset: 0;
            background: rgba(0,0,0,0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
            transition: opacity 0.25s;
        }}
        .play-overlay.hidden {{
            opacity: 0;
            pointer-events: none;
        }}
        .play-circle-btn {{
            width: 80px;
            height: 80px;
            background: #00A896;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            transition: transform 0.2s, background 0.2s;
        }}
        .play-circle-btn:hover {{
            transform: scale(1.1);
            background: #02C39A;
        }}
        .play-icon {{
            width: 0; 
            height: 0; 
            border-top: 16px solid transparent;
            border-bottom: 16px solid transparent;
            border-left: 26px solid #000000;
            margin-left: 6px;
        }}
        
        /* Modern Video Scrubber & Control Bar */
        .video-control-bar {{
            background: #091A1C;
            padding: 12px 18px;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        }}
        
        /* Scrubber Progress Bar */
        .progress-track {{
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.15);
            border-radius: 4px;
            cursor: pointer;
            position: relative;
            transition: height 0.15s;
        }}
        .progress-track:hover {{
            height: 10px;
        }}
        .progress-fill {{
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #028090, #00A896);
            border-radius: 4px;
            position: relative;
        }}
        .progress-thumb {{
            width: 14px;
            height: 14px;
            background: #FFFFFF;
            border-radius: 50%;
            position: absolute;
            right: -7px;
            top: 50%;
            transform: translateY(-50%);
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        }}
        
        .controls-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .ctrl-group-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .btn-ctrl {{
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.18);
            color: #FFFFFF;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .btn-ctrl:hover {{
            background: #00A896;
            color: #000000;
            border-color: #00A896;
        }}
        
        .time-display {{
            font-size: 0.9rem;
            font-weight: 600;
            color: #A0B9BA;
            font-variant-numeric: tabular-nums;
        }}
        
        .chapter-title {{
            font-size: 0.9rem;
            font-weight: 600;
            color: #00A896;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <div class="video-player-card">
        <!-- 16:9 Presentation Screen -->
        <div class="video-screen" id="videoScreen" onclick="togglePlay()">
            <div class="circle-tr"></div>
            <div class="circle-br"></div>
            
            <div class="mintbook-logo-card">
                {logo_img_tag}
            </div>
            
            <div class="slide-content-area">
                <h1 class="slide-title-text" id="screenTitle">Loading Video...</h1>
                <div class="title-divider-line"></div>
                <ul class="bullets-container" id="screenBullets"></ul>
            </div>
            
            <div class="vydia-branding">
                <div class="dots-row">
                    <div class="dot dot-1"></div>
                    <div class="dot dot-2"></div>
                </div>
                <div class="vydia-text">VYDIA.AI</div>
                <div class="mintbook-product-text">A Mintbook Product</div>
            </div>
            
            <div class="slide-counter-number" id="screenSlideNum">01</div>
            
            <!-- Play / Pause Overlay -->
            <div class="play-overlay" id="playOverlay">
                <div class="play-circle-btn">
                    <div class="play-icon"></div>
                </div>
            </div>
        </div>
        
        <!-- Video Control Scrubber -->
        <div class="video-control-bar">
            <!-- Scrubber Track -->
            <div class="progress-track" id="progressTrack" onclick="seekVideo(event)">
                <div class="progress-fill" id="progressFill">
                    <div class="progress-thumb"></div>
                </div>
            </div>
            
            <div class="controls-row">
                <div class="ctrl-group-left">
                    <button class="btn-ctrl" id="playBtn" onclick="togglePlay()">▶️ Play</button>
                    <button class="btn-ctrl" onclick="jumpSlide(-1)">⏮️</button>
                    <button class="btn-ctrl" onclick="jumpSlide(1)">⏭️</button>
                    <div class="time-display" id="timeDisplay">0:00 / 0:00</div>
                </div>
                <div class="chapter-title" id="chapterTitle">Slide 1: Introduction</div>
                <div>
                    <button class="btn-ctrl" onclick="toggleFullScreen()">⛶ Fullscreen</button>
                </div>
            </div>
        </div>
    </div>
    
    <audio id="audioElement"></audio>

    <script>
        const slides = {json.dumps(slides_data)};
        const totalDuration = {total_time};
        let currentSlideIdx = 0;
        let isPlaying = false;
        let currentTime = 0;
        let animationFrameId = null;
        
        const audio = document.getElementById('audioElement');
        const progressFill = document.getElementById('progressFill');
        const timeDisplay = document.getElementById('timeDisplay');
        const playBtn = document.getElementById('playBtn');
        const playOverlay = document.getElementById('playOverlay');
        const chapterTitle = document.getElementById('chapterTitle');

        function formatTime(seconds) {{
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;
        }}

        function renderSlideVisual(index) {{
            const s = slides[index];
            const titleEl = document.getElementById('screenTitle');
            const divider = document.querySelector('.title-divider-line');
            titleEl.innerText = s.title;
            
            const list = document.getElementById('screenBullets');
            list.innerHTML = '';
            
            if (s.bullets.length === 0) {{
                titleEl.classList.add('centered-title');
                if(divider) divider.style.display = 'none';
            }} else {{
                titleEl.classList.remove('centered-title');
                if(divider) divider.style.display = 'block';
                s.bullets.forEach(b => {{
                    const li = document.createElement('li');
                    li.className = 'bullet-point';
                    li.innerText = b;
                    list.appendChild(li);
                }});
            }}

            const seq = s.index < 10 ? '0' + s.index : s.index;
            document.getElementById('screenSlideNum').innerText = seq;
            chapterTitle.innerText = `Slide ${{s.index}}: ${{s.title}}`;
        }}

        function updateProgressUI() {{
            const pct = Math.min(100, Math.max(0, (currentTime / totalDuration) * 100));
            progressFill.style.width = pct + '%';
            timeDisplay.innerText = `${{formatTime(currentTime)}} / ${{formatTime(totalDuration)}}`;
        }}

        function findSlideForTime(t) {{
            for (let i = 0; i < slides.length; i++) {{
                if (t >= slides[i].start_time && t < slides[i].end_time) {{
                    return i;
                }}
            }}
            return slides.length - 1;
        }}

        function syncToTime(newTime, forcePlay) {{
            currentTime = Math.min(totalDuration, Math.max(0, newTime));
            const newSlideIdx = findSlideForTime(currentTime);
            
            const slideChanged = (newSlideIdx !== currentSlideIdx);
            currentSlideIdx = newSlideIdx;
            renderSlideVisual(currentSlideIdx);
            
            const currentSlide = slides[currentSlideIdx];
            const slideOffset = currentTime - currentSlide.start_time;

            if (slideChanged || audio.src !== currentSlide.audio_b64) {{
                audio.src = currentSlide.audio_b64;
                audio.currentTime = Math.max(0, slideOffset);
                if (isPlaying || forcePlay) {{
                    audio.play().catch(e => console.log(e));
                }}
            }} else {{
                audio.currentTime = Math.max(0, slideOffset);
            }}
            updateProgressUI();
        }}

        function playbackTick() {{
            if (isPlaying) {{
                const currentSlide = slides[currentSlideIdx];
                if (!audio.paused && audio.duration) {{
                    currentTime = currentSlide.start_time + audio.currentTime;
                }}
                
                updateProgressUI();

                // Advance to next slide if audio finished or time exceeded
                if (audio.ended || currentTime >= currentSlide.end_time) {{
                    if (currentSlideIdx < slides.length - 1) {{
                        currentSlideIdx++;
                        renderSlideVisual(currentSlideIdx);
                        audio.src = slides[currentSlideIdx].audio_b64;
                        audio.currentTime = 0;
                        audio.play().catch(e => console.log(e));
                    }} else {{
                        // Finished
                        pauseVideo();
                        currentTime = totalDuration;
                        updateProgressUI();
                        return;
                    }}
                }} else {{
                    animationFrameId = requestAnimationFrame(playbackTick);
                }}
            }}
        }}

        function playVideo() {{
            if (currentTime >= totalDuration) {{
                currentTime = 0;
                currentSlideIdx = 0;
            }}
            isPlaying = true;
            playBtn.innerText = '⏸️ Pause';
            playOverlay.classList.add('hidden');
            
            const currentSlide = slides[currentSlideIdx];
            if (audio.src !== currentSlide.audio_b64) {{
                audio.src = currentSlide.audio_b64;
                audio.currentTime = currentTime - currentSlide.start_time;
            }}
            audio.play().then(() => {{
                animationFrameId = requestAnimationFrame(playbackTick);
            }}).catch(e => console.log(e));
        }}

        function pauseVideo() {{
            isPlaying = false;
            playBtn.innerText = '▶️ Play';
            playOverlay.classList.remove('hidden');
            audio.pause();
            if (animationFrameId) cancelAnimationFrame(animationFrameId);
        }}

        function togglePlay() {{
            if (isPlaying) {{
                pauseVideo();
            }} else {{
                playVideo();
            }}
        }}

        function seekVideo(e) {{
            const rect = document.getElementById('progressTrack').getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            const targetTime = pos * totalDuration;
            syncToTime(targetTime, isPlaying);
        }}

        function jumpSlide(direction) {{
            const targetIdx = Math.min(slides.length - 1, Math.max(0, currentSlideIdx + direction));
            syncToTime(slides[targetIdx].start_time, isPlaying);
        }}

        function toggleFullScreen() {{
            const elem = document.getElementById('videoScreen');
            if (!document.fullscreenElement) {{
                elem.requestFullscreen().catch(err => console.log(err));
            }} else {{
                document.exitFullscreen();
            }}
        }}

        // Initialize at Slide 1 (0:00)
        renderSlideVisual(0);
        updateProgressUI();
    </script>
</body>
</html>
"""
        html_path = os.path.join(output_dir, "presentation.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_path
