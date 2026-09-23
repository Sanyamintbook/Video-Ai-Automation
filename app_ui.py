import os
import sys
import time
import json
import asyncio
import uuid
from pathlib import Path
import streamlit as st
import streamlit_shadcn_ui as ui

# Set page configuration
st.set_page_config(
    page_title="Olympiad AI Video Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import get_settings
from app.infrastructure.queue.tasks import run_full_pipeline
from app.infrastructure.state.sqlite_store import get_job, get_all_jobs, save_job

# Custom CSS styling for a polished, modern interface
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0ea5e9;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .status-running { background-color: #0369a1; color: #e0f2fe; }
    .status-done { background-color: #047857; color: #d1fae5; }
    .status-failed { background-color: #b91c1c; color: #fee2e2; }
    
    /* Subtle button hover lift */
    .stButton>button {
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)# ==========================================
# SIDEBAR CONTROLS & PARAMETERS
# ==========================================
st.sidebar.markdown("## ⚙️ Generation Settings")

custom_output_dir = str(PROJECT_ROOT / "outputs_v3")

# 1. Output Destination
st.sidebar.markdown("### 📂 Final Video Save Location")

if "final_save_dir" not in st.session_state:
    st.session_state.final_save_dir = str(PROJECT_ROOT / "outputs_v3")

user_output_dir = st.sidebar.text_input("Folder Path", value=st.session_state.final_save_dir, label_visibility="collapsed")

if st.sidebar.button("📁 Browse Directory", use_container_width=True):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    selected_folder = filedialog.askdirectory(master=root)
    if selected_folder:
        st.session_state.final_save_dir = selected_folder
        st.rerun()

st.session_state.final_save_dir = user_output_dir
st.sidebar.caption("All intermediate files (audio, scripts) will be saved in `outputs_v3`. Only the final video will be copied to this location.")

st.sidebar.divider()

# 2. Visual & Template Styling
st.sidebar.markdown("### 🎨 Slide Template")
custom_template_file = st.sidebar.file_uploader(
    "Upload Custom PPTX Template (Optional)",
    type=["pptx"],
    help="Upload your own .pptx slide template. If none is uploaded, the official Mintbook corporate template is used automatically."
)

if custom_template_file:
    st.sidebar.success(f"📌 Using custom template: `{custom_template_file.name}`")
else:
    st.sidebar.info("📌 Using Default: **Official Mintbook Template**")

# Hardcoded Default Engine Options (Hidden from UI)
title_color = "#FFFFFF"
body_color = "#E2E8F0"
accent_color = "#14B8A6"
bg_color = "#0B3436"
voice_name = "af_heart"
speed_rate = 1.0
resolution_code = "1080p"
provider_code = "ollama"
model_choice = "qwen2.5:7b"

from streamlit_option_menu import option_menu

st.markdown('<div class="main-header">🎬 Olympiad AI Video Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated End-to-End Educational PDF to Synchronized Video Generator</div>', unsafe_allow_html=True)

selected_tab = option_menu(
    menu_title=None,
    options=["Generate Video", "Job History", "System Architecture"],
    icons=["play-btn", "clock-history", "diagram-3"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent", "border-radius": "10px", "margin-bottom": "20px"},
        "icon": {"color": "#0ea5e9", "font-size": "18px"},
        "nav-link": {"font-size": "15px", "text-align": "center", "margin": "0px"},
        "nav-link-selected": {"background-color": "#0ea5e9", "color": "#ffffff", "border-radius": "8px"},
    }
)

# ----------------------------------------------------
# TAB 1: GENERATE VIDEO
# ----------------------------------------------------
if selected_tab == "Generate Video":
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    main_col1, main_col2 = st.columns([1, 1.2], gap="large")
    
    with main_col1:
        with st.container(border=True):
            st.markdown("### 📝 Create your video")
            st.markdown("<span style='opacity: 0.7;'>Choose details & upload your PDF.</span>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            coverage_mode = st.selectbox(
                "📚 Curriculum Coverage",
                ["Full Auto-Extract (100% Quality)", "Standard Lesson (8-15 slides)", "Concise Summary (4-6 slides)"],
                index=0
            )
            
            page_range = st.text_input("📄 Page Range (Optional)", value="All", help="e.g. '1-10' or 'All'")
            
            st.markdown("<br>", unsafe_allow_html=True)
            uploaded_pdf = st.file_uploader("📂 UPLOAD PDF", type=["pdf"], help="Supports any textbook chapter, study notes, or curriculum PDF.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            generate_btn = st.button("▶ Generate Video", type="primary", use_container_width=True, disabled=(uploaded_pdf is None))
            
            if not uploaded_pdf:
                st.info("↑ Upload a PDF to start generation.")

    with main_col2:
        with st.container(border=True):
            st.markdown("""
            <div style="text-align: center; padding: 20px 0;">
                <div style="background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%); width: 70px; height: 70px; border-radius: 20px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3);">
                    <h1 style="color: white; margin: 0;">▶</h1>
                </div>
                <h3 style="margin-bottom: 10px;">Your AI teaching studio is ready</h3>
                <p style="opacity: 0.7; font-size: 15px; max-width: 90%; margin: 0 auto; line-height: 1.5;">Upload a PDF and our pipeline will extract the content, plan the lesson, write the script, generate a voiceover and render a complete video — automatically.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="display: flex; flex-direction: column; gap: 20px; margin-top: 20px; padding: 0 20px;">
                <div>
                    <h4>🎙️ Natural voiceover</h4>
                    <p style="font-size: 14px; opacity: 0.8; margin-top: -5px;">Human-like narration generated dynamically in your chosen language.</p>
                </div>
                <div>
                    <h4>📊 Auto slides</h4>
                    <p style="font-size: 14px; opacity: 0.8; margin-top: -5px;">Textbooks and examples turned into beautiful, animated presentations.</p>
                </div>
                <div>
                    <h4>🎬 HD video export</h4>
                    <p style="font-size: 14px; opacity: 0.8; margin-top: -5px;">Ready to download, share, or upload anywhere.</p>
                </div>
            </div>
            <br>
            """, unsafe_allow_html=True)

    if generate_btn and uploaded_pdf is not None:
        # Prepare job metadata
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        safe_name = "".join(c for c in uploaded_pdf.name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
        name_without_ext = os.path.splitext(safe_name)[0]
        
        # Append short job_id to make every run's output folder completely unique
        document_id = f"{name_without_ext}_{job_id.split('_')[1]}"
        
        doc_output_dir = os.path.join(custom_output_dir, document_id)
        os.makedirs(doc_output_dir, exist_ok=True)
        
        pdf_path = os.path.join(doc_output_dir, safe_name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
            
        # Handle custom template if uploaded
        template_path = None
        if custom_template_file:
            template_path = os.path.join(doc_output_dir, "custom_template.pptx")
            with open(template_path, "wb") as f:
                f.write(custom_template_file.getbuffer())
                
        pipeline_options = {
            "template_path": template_path,
            "title_color": title_color,
            "body_color": body_color,
            "accent_color": accent_color,
            "bg_color": bg_color,
            "voice": voice_name,
            "speed": speed_rate,
            "resolution": resolution_code,
            "coverage_mode": coverage_mode,
            "provider": provider_code,
            "model": model_choice
        }
        
        save_job(job_id, {
            "document_id": document_id,
            "status": "RUNNING",
            "stage": "parsing",
            "output_dir": doc_output_dir,
            "options": pipeline_options
        })
        
        progress_bar = st.progress(0, text="Initializing Pipeline...")
        status_container = st.empty()
        
        # Async execution within Streamlit
        async def run_pipeline_with_progress():
            task = asyncio.create_task(run_full_pipeline(job_id, document_id, pdf_path, doc_output_dir, pipeline_options))
            
            stage_map = {
                "parsing": (15, "[1/6] Ingesting PDF & Building FAISS Vector Store..."),
                "understanding": (35, "[2/6] Deep Content Understanding (Map-Reduce)..."),
                "lesson_planning": (50, "[3/6] Structuring Lesson Plan & Subtopics..."),
                "unit_planning": (65, "[4/6] Generating Slides & Querying RAG Context..."),
                "audio_synthesis": (85, "[5/6] Synthesizing Voice Narration & Slide Images..."),
                "completed": (100, "[6/6] Finalizing Video & PowerPoint Assembly!")
            }
            
            while not task.done():
                current_job = get_job(job_id)
                current_stage = current_job.get("stage", "parsing")
                percent, stage_desc = stage_map.get(current_stage, (20, f"Processing {current_stage}..."))
                
                # Check units progress if in audio_synthesis
                units_total = current_job.get("units_total", 0)
                units_done = current_job.get("units_done", 0)
                if units_total > 0 and current_stage == "audio_synthesis":
                    sub_pct = int(65 + (units_done / units_total) * 25)
                    stage_desc = f"[5/6] Synthesizing Slide {units_done}/{units_total} Audio & Layout..."
                    percent = min(92, sub_pct)
                    
                progress_bar.progress(percent, text=stage_desc)
                await asyncio.sleep(2)
                
            await task
            job_final = get_job(job_id)
            if job_final.get("status") == "FAILED":
                raise Exception(job_final.get("failure_reason", "Pipeline encountered an error during execution."))
            progress_bar.progress(100, text="🎉 Video Generation Successfully Completed!")

        # Execute
        try:
            with st.spinner("Processing AI Video Generation Pipeline..."):
                asyncio.run(run_pipeline_with_progress())
                
            st.success("✅ Video Generation Finished Successfully!")
            
            final_video = os.path.join(doc_output_dir, "video.mp4")
            final_pptx = os.path.join(doc_output_dir, "output.pptx")
            final_script = os.path.join(doc_output_dir, "script.json")
            final_html = os.path.join(doc_output_dir, "presentation.html")
            
            import shutil
            if os.path.exists(final_video):
                shutil.copy(final_video, os.path.join(user_output_dir, f"{document_id}_video.mp4"))
            if os.path.exists(final_pptx):
                shutil.copy(final_pptx, os.path.join(user_output_dir, f"{document_id}_presentation.pptx"))
            if os.path.exists(final_html):
                shutil.copy(final_html, os.path.join(user_output_dir, f"{document_id}_interactive.html"))
            
            st.markdown("### 🎥 Generated Educational Video & Presentation Studio")
            
            slide_files = sorted(list(Path(doc_output_dir).glob("slide_*.json")))
            final_html = os.path.join(doc_output_dir, "presentation.html")
            if os.path.exists(final_html):
                st.markdown("#### 📽️ Interactive Synchronized AI Presentation & Audio Player")
                with open(final_html, "r", encoding="utf-8") as hf:
                    html_code = hf.read()
                import streamlit.components.v1 as components
                components.html(html_code, height=720)
                st.markdown("---")
            elif slide_files:
                st.markdown("#### 📽️ Interactive Slide & Synchronized Audio Player")
                
                if "current_slide_idx" not in st.session_state:
                    st.session_state.current_slide_idx = 0
                    
                cur_idx = st.session_state.current_slide_idx
                if cur_idx >= len(slide_files):
                    cur_idx = 0
                    st.session_state.current_slide_idx = 0
                    
                # Load current slide data
                with open(slide_files[cur_idx], "r", encoding="utf-8") as sf:
                    cur_slide = json.load(sf)
                    
                u_id = cur_slide.get("unit_id", "")
                aud_path = os.path.join(doc_output_dir, "audio", f"{u_id}.wav")
                
                # Render Slide Card Visual
                st.markdown(f"""
                <div style="background: {bg_color}; border-radius: 12px; padding: 28px 36px; color: {body_color}; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
                    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 16px;">
                        <span style="background: {accent_color}; color: #000; font-weight: 800; padding: 4px 14px; border-radius: 8px; font-size: 1.1rem;">Slide {cur_idx + 1:02d} / {len(slide_files):02d}</span>
                        <h2 style="color: {title_color}; margin: 0; font-size: 1.4rem; font-weight: 700;">{cur_slide.get('title', '')}</h2>
                    </div>
                    <hr style="border: 0; height: 1px; background: rgba(255,255,255,0.15); margin: 12px 0 20px 0;" />
                    <ul style="font-size: 1.1rem; line-height: 1.8; margin-left: 20px;">
                        {''.join([f"<li style='margin-bottom: 8px;'>{b}</li>" for b in cur_slide.get('bullets', [])])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Slide Audio Player
                if os.path.exists(aud_path):
                    st.audio(aud_path, format="audio/wav")
                    
                # Controls
                c_prev, c_space, c_next = st.columns([1, 2, 1])
                with c_prev:
                    if st.button("⬅️ Previous Slide", disabled=(cur_idx == 0), use_container_width=True):
                        st.session_state.current_slide_idx = max(0, cur_idx - 1)
                        st.rerun()
                with c_next:
                    if st.button("Next Slide ➡️", disabled=(cur_idx == len(slide_files) - 1), use_container_width=True):
                        st.session_state.current_slide_idx = min(len(slide_files) - 1, cur_idx + 1)
                        st.rerun()
                        
                st.markdown("---")

            if os.path.exists(final_video):
                st.video(final_video)
                with open(final_video, "rb") as vf:
                    st.download_button("📥 Download MP4 Video", data=vf, file_name=f"{name_without_ext}_video.mp4", mime="video/mp4")
                
            final_html = os.path.join(doc_output_dir, "presentation.html")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                if os.path.exists(final_pptx):
                    with open(final_pptx, "rb") as pf:
                        st.download_button("📥 Download PowerPoint (.pptx)", data=pf, file_name=f"{name_without_ext}_slides.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)
            with col_d2:
                if os.path.exists(final_html):
                    with open(final_html, "rb") as hf:
                        st.download_button("🌐 Download HTML5 Presentation (.html)", data=hf, file_name=f"{name_without_ext}_presentation.html", mime="text/html", use_container_width=True)
            with col_d3:
                if os.path.exists(final_script):
                    with open(final_script, "rb") as sf:
                        st.download_button("📜 Download Script (.json)", data=sf, file_name=f"{name_without_ext}_script.json", mime="application/json", use_container_width=True)
                        
        except Exception as ex:
            st.error(f"❌ Error during generation: {str(ex)}")


# ----------------------------------------------------
# TAB 2: JOB HISTORY & RESUME
# ----------------------------------------------------
elif selected_tab == "Job History":
    st.markdown("### 📊 Persistent Job History")
    recent_jobs = get_all_jobs(limit=25)
    
    if not recent_jobs:
        st.info("No previous jobs found in database.")
    else:
        for j in recent_jobs:
            j_id = j.get("job_id")
            doc_id = j.get("document_id", "Unknown")
            status = j.get("status", "PENDING")
            stage = j.get("stage", "Unknown")
            updated = j.get("updated_at", "")
            out_dir = j.get("output_dir", "")
            
            badge_class = "status-running" if status == "RUNNING" else ("status-done" if status == "DONE" else "status-failed")
            
            with st.expander(f"📁 {doc_id} [{status}] - {updated[:19]}", expanded=(status == "RUNNING")):
                st.markdown(f"**Job ID**: `{j_id}` | **Status**: <span class='status-badge {badge_class}'>{status}</span> | **Stage**: `{stage}`", unsafe_allow_html=True)
                st.markdown(f"**Output Directory**: `{out_dir}`")
                
                v_path = os.path.join(out_dir, "video.mp4") if out_dir else ""
                if os.path.exists(v_path):
                    st.video(v_path)
                elif status == "RUNNING":
                    st.info("This job is currently in progress or was interrupted.")


# ----------------------------------------------------
# TAB 3: SYSTEM ARCHITECTURE & GUIDE
# ----------------------------------------------------
elif selected_tab == "System Architecture":
    st.markdown("""
    ### 🏗️ Complete Pipeline Architecture
    
    1. **PyMuPDF Ingestion & FAISS Vector Store**:
       - Extracts full structured text from textbooks.
       - Recursively chunks text (1,000 chars) and creates local embeddings with `mxbai-embed-large`.
    
    2. **Map-Reduce Content Understanding (Zero Quality Loss)**:
       - Slices chapters into 6,500-character segments to prevent LLM context overflow.
       - Extracts 100% of subtopics, definitions, and learning objectives without hallucination.
       
    3. **Batched Slide & Narration Generation**:
       - Generates 5 slides per batch with dynamic RAG context retrieval.
       - Synthesizes teacher-style spoken explanations and validates grounding.
       
    4. **Local Neural TTS (Kokoro ONNX)**:
       - High-fidelity voice synthesis (`af_heart`, `af_bella`, `am_adam`).
       - Measures real duration directly from generated WAV audio files.
       
    5. **Branded PPTX & Multi-Threaded FFmpeg Video Rendering**:
       - Binds titles and bullets to PowerPoint templates with custom styling and speaker notes.
       - Exports slides to high-resolution PNGs and stitches audio with FFmpeg into MP4.
    """)
