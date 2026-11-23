from functools import lru_cache

from app.config import settings
from app.llm.base import LLMClient


@lru_cache
def get_llm(small: bool = False) -> LLMClient:
    """Factory: đổi provider bằng cấu hình, code agent không đổi (Dependency Inversion)."""
    if settings.llm_provider == "fake":
        from app.llm.fake import RuleBasedFakeLLM

        return RuleBasedFakeLLM()
    if settings.llm_provider == "local":
        raise NotImplementedError("LLM_PROVIDER=local mới hỗ trợ bước RAG; agent loop cần claude/fake")
    from app.llm.claude import ClaudeClient

    model = settings.anthropic_small_model if small else settings.anthropic_model
    return ClaudeClient(model=model, effort=settings.llm_effort, fallbacks=settings.llm_fallbacks)
