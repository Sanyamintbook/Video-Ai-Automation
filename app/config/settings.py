"""Application settings loaded from environment variables and .env."""

import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Try to load .env file
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(str(env_file))
except Exception:
    pass


class Settings:
    """
    Global application configuration.
    Robust against any Pydantic version or environment constraints.
    """
    def __init__(self):
        # Application
        self.app_name: str = os.getenv("APP_NAME", "Olympiad AI Video Generator")
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # AI Providers
        self.google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.ollama_fallback_url: str = os.getenv("OLLAMA_FALLBACK_URL", "http://127.0.0.1:11434")
        self.ollama_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b")
        self.ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large:latest")
        self.ollama_embedding_timeout_seconds: float = float(os.getenv("OLLAMA_EMBEDDING_TIMEOUT", "3600.0"))
        self.ollama_request_timeout_seconds: float = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "3600.0"))
        self.ollama_connect_timeout_seconds: float = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "15.0"))
        self.ollama_max_retries: int = int(os.getenv("OLLAMA_MAX_RETRIES", "2"))
        self.ollama_retry_backoff_seconds: float = float(os.getenv("OLLAMA_RETRY_BACKOFF", "2.0"))
        self.ollama_num_predict: int = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
        self.ollama_context_window: int = int(os.getenv("OLLAMA_CONTEXT_WINDOW", "8192"))
        self.ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
        self.llm_content_char_limit: int = int(os.getenv("LLM_CONTENT_CHAR_LIMIT", "8000"))
        self.llm_source_context_char_limit: int = int(os.getenv("LLM_SOURCE_CONTEXT_CHAR_LIMIT", "6000"))
        self.max_local_retries_before_escalation: int = 2

        self.default_provider: str = os.getenv("DEFAULT_PROVIDER", "ollama")
        self.default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b")

        # Directories
        upload_dir = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads"))
        self.upload_directory: str = str(Path(upload_dir) if Path(upload_dir).is_absolute() else PROJECT_ROOT / upload_dir)

        output_dir = os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "output_new"))
        self.output_directory: str = str(Path(output_dir) if Path(output_dir).is_absolute() else PROJECT_ROOT / output_dir)

        prompts_dir = os.getenv("PROMPTS_DIR", str(PROJECT_ROOT / "prompts"))
        self.prompts_directory: str = str(Path(prompts_dir) if Path(prompts_dir).is_absolute() else PROJECT_ROOT / prompts_dir)

        # Rendering & FFmpeg resolution
        ffmpeg_bin = os.getenv("FFMPEG_PATH", "ffmpeg")
        if shutil.which(ffmpeg_bin):
            self.ffmpeg_path: str = ffmpeg_bin
        else:
            winget_pkgs = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
            found = list(winget_pkgs.glob("**/ffmpeg.exe")) if winget_pkgs.exists() else []
            if found:
                self.ffmpeg_path: str = str(found[0])
            else:
                self.ffmpeg_path: str = "ffmpeg"

        self.tts_model: str = os.getenv("TTS_MODEL", "tts-1")
        self.tts_voice: str = os.getenv("TTS_VOICE", "alloy")
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a singleton Settings instance.
    """
    return Settings()
