from pydantic import BaseModel


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
