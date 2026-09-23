import pytest
from app.infrastructure.ai.providers.router import Router
from app.infrastructure.ai.providers.ollama_provider import OllamaProvider
from app.infrastructure.ai.providers.gemini_provider import GeminiProvider

def test_router_default():
    router = Router()
    provider = router.select_provider(agent_name="TestAgent", retry_count=0, failure_type=None)
    assert isinstance(provider, OllamaProvider)

def test_router_first_schema_failure_no_escalation():
    router = Router()
    provider = router.select_provider(agent_name="TestAgent", retry_count=0, failure_type="schema")
    assert isinstance(provider, OllamaProvider)
    
    provider = router.select_provider(agent_name="TestAgent", retry_count=1, failure_type="schema")
    assert isinstance(provider, OllamaProvider)

def test_router_third_schema_failure_escalates():
    router = Router()
    provider = router.select_provider(agent_name="TestAgent", retry_count=2, failure_type="schema")
    assert isinstance(provider, GeminiProvider)

def test_router_unreachable_immediate_escalation():
    router = Router()
    provider = router.select_provider(agent_name="TestAgent", retry_count=0, failure_type="unreachable")
    assert isinstance(provider, GeminiProvider)
