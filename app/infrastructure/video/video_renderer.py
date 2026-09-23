import os
import re
import json
import base64
import subprocess
import tempfile
import logging
import concurrent.futures
from pathlib import Path
from typing import List

from app.domain.models.timeline import TimelineEntry
from app.domain.models.video import Video
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def generate_slide_png(
    title: str,
    bullets: list,
    seq: int,
    output_png: Path,
    bg_hex: str = "#083335",
    title_hex: str = "#FFFFFF",
    body_hex: str = "#E2E8F0",
    accent_hex: str = "#00A896"
):
    from PIL import Image, ImageDraw, ImageFont
    import math

    width, height = 1920, 1080
    img = Image.new("RGB", (width, height), bg_hex)
    draw = ImageDraw.Draw(img)

    # Top Right Curved Teal Arc
    # cx=1780, cy=-60, r=460 -> bbox=(1780-460, -60-460, 1780+460, -60+460)
    draw.ellipse((1320, -520, 2240, 400), fill="#028090")

    # Bottom Right Curved Cyan Arc
    # cx=1860, cy=1000, r=320 -> bbox=(1860-320, 1000-320, 1860+320, 1000+320)
    draw.ellipse((1540, 680, 2180, 1320), fill="#00A896")

    # Mintbook Logo Card (Top Right)
    # rect x=1560, y=44, w=230, h=54, rx=8
    draw.rounded_rectangle((1560, 44, 1560+230, 44+54), radius=8, fill="#FFFFFF")
    
    # Load Fonts
    font_title = ImageFont.truetype("arial.ttf", 64)
    font_body = ImageFont.truetype("arial.ttf", 42)
    font_bullet = ImageFont.truetype("arial.ttf", 46)
    font_small = ImageFont.truetype("arial.ttf", 26)
    font_tiny = ImageFont.truetype("arial.ttf", 20)
    font_seq = ImageFont.truetype("arial.ttf", 40)

    # Logo Image
    logo_path = Path(__file__).resolve().parent.parent / "presentation" / "assets" / "mintbook_logo.png"
    if logo_path.exists():
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_img = logo_img.resize((190, 38))
        img.paste(logo_img, (1580, 52), logo_img)
    else:
        draw.text((1675, 71), "mintbook", font=font_small, fill="#083335", anchor="mm")

    # Slide Title & Content
    t_text = title.title()
    if not bullets:
        # Center horizontally and vertically
        bbox = draw.textbbox((0, 0), t_text, font=font_title)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        # Shift slightly up from perfect center for visual balance
        draw.text(((width - w) / 2, (height - h) / 2 - 40), t_text, font=font_title, fill=title_hex)
    else:
        # Standard top-left title
        draw.text((90, 115), t_text, font=font_title, fill=title_hex)
        
        # Divider Line
        draw.line([(90, 200), (500, 200)], fill="#FFFFFF", width=2)
        draw.line([(90, 200), (250, 200)], fill=accent_hex, width=2)

        # Bullet Points
        y_offset = 260
    import textwrap
    for b in bullets:
        wrapped_lines = textwrap.wrap(b, width=75)
        draw.text((90, y_offset-4), "•", font=font_bullet, fill=accent_hex)
        for line in wrapped_lines:
            draw.text((130, y_offset), line, font=font_body, fill=body_hex)
            y_offset += 60
        y_offset += 40

    # Bottom Left VYDIA Branding
    draw.ellipse((90-8, 980-8, 90+8, 980+8), fill="#02C39A")
    draw.ellipse((114-8, 980-8, 114+8, 980+8), fill="#00A896")
    draw.text((90, 1010), "VYDIA.AI", font=font_small, fill="#6FA9A6")
    draw.text((90, 1040), "A Mintbook Product", font=font_tiny, fill="#6FA9A6")

    # Bottom Right Slide Number
    draw.text((1830, 1030), f"{seq:02d}", font=font_seq, fill="#FFFFFF", anchor="mm")

    img.save(output_png)


class VideoRenderer:
    """
    Renders the final MP4 video by converting slide frames and audio clips into HD video segments,
    then concatenating them seamlessly via FFmpeg.
    """

    @staticmethod
    def render(
        document_id: str,
        pptx_path: str,
        timeline: List[TimelineEntry],
        output_path: str,
        resolution: str = "1080p"
    ) -> Video:
        settings = get_settings()
        ffmpeg_cmd = settings.ffmpeg_path
        
        scale_w = 1920 if resolution == "1080p" else 1280
        scale_h = 1080 if resolution == "1080p" else 720
        
        doc_dir = Path(os.path.dirname(os.path.abspath(pptx_path)))
        
        # Load units strictly in order
        units_file = doc_dir / "teaching_units.json"
        units_data = []
        if units_file.exists():
            try:
                with open(units_file, "r", encoding="utf-8") as uf:
                    units_data = json.load(uf)
                units_data.sort(key=lambda x: x.get("order", 0))
            except Exception:
                pass
                
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            slides_folder = temp_path / "slides"
            slides_folder.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Generating HD slide graphics in {slides_folder}...")
            
            # Generate SVGs for all slides in strict chronological order
            svg_files = []
            for i, entry in enumerate(timeline):
                slide_num = i + 1
                title = f"Slide {slide_num}"
                bullets = ["Educational content analysis."]
                
                if i < len(units_data):
                    u = units_data[i]
                    raw_title = u.get("learning_goal", title)
                    if " - " in raw_title:
                        title = raw_title.split(" - ")[-1].strip()
                    elif ": " in raw_title:
                        title = raw_title.split(": ")[-1].strip()
                    elif " & " in raw_title and len(raw_title) > 40:
                        title = raw_title.split(" & ")[0].strip()
                    else:
                        title = raw_title
                    words = title.split()
                    if len(words) > 7:
                        title = " ".join(words[:7])
                    bullets = u.get("bullet_sentences", bullets)
                        
                # Generate PNG directly using Pillow
                png_file = slides_folder / f"Slide{slide_num}.png"
                generate_slide_png(title, bullets, slide_num, png_file)
                
                # Resize to target resolution if not 1080p
                if scale_w != 1920 or scale_h != 1080:
                    from PIL import Image
                    img = Image.open(png_file)
                    img = img.resize((scale_w, scale_h), Image.Resampling.LANCZOS)
                    img.save(png_file)
                    
                svg_files.append(png_file)
                
            segment_files = []
            render_tasks = []
            for i, entry in enumerate(timeline):
                slide_num = i + 1
                img_file = svg_files[i] if i < len(svg_files) else svg_files[-1]
                audio_file = Path(entry.audio_path)
                segment_file = temp_path / f"segment_{slide_num}.mp4"
                segment_files.append(segment_file)
                duration = entry.slide_end_sec - entry.slide_start_sec
                render_tasks.append((slide_num, img_file, audio_file, segment_file, duration))
                
            def _render_single_segment(task_info):
                slide_num, img_f, aud_f, seg_f, duration = task_info
                cmd = [
                    ffmpeg_cmd,
                    "-y",
                    "-nostdin",
                    "-loop", "1",
                    "-i", str(img_f),
                    "-i", str(aud_f),
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "18",
                    "-tune", "stillimage",
                    "-c:a", "pcm_s16le",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    str(seg_f)
                ]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    logger.error(f"FFmpeg failed for segment {slide_num}: {e.stderr.decode(errors='ignore')}")
                    raise
                
            max_workers = 1
            logger.info(f"Rendering video segments sequentially to prevent system overload...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_render_single_segment, render_tasks))
                
            # Concatenate all slide video segments
            concat_list_path = Path(temp_dir) / "concat_list.txt"
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for sf in segment_files:
                    f.write(f"file '{sf.as_posix()}'\n")
                    
            logger.info(f"Concatenating all {len(segment_files)} segments into final video...")
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            concat_cmd = [
                ffmpeg_cmd,
                "-y",
                "-nostdin",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            try:
                subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg concat failed: {e.stderr.decode(errors='ignore')}")
                raise
            
            total_duration = sum(entry.slide_end_sec - entry.slide_start_sec for entry in timeline)
            logger.info(f"Video rendering complete! Saved to {output_path} (Duration: {total_duration:.1f}s)")
            
            return Video(
                document_id=document_id,
                storage_path=output_path,
                duration_sec=total_duration
            )
