from pathlib import Path

from app.config.settings import get_settings


class PromptLoader:
    def __init__(self) -> None:
        settings = get_settings()
        self.prompt_directory = Path(settings.prompts_directory)

    def load(self, prompt_name: str) -> str:
        path = self.prompt_directory / f"{prompt_name}.md"

        if not path.exists():
            raise FileNotFoundError(f"Prompt '{prompt_name}' not found.")

        return path.read_text(encoding="utf-8")