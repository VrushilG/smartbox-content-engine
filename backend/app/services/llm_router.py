from types import ModuleType

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_service() -> ModuleType:
    """Return the appropriate LLM service module based on configuration.

    Priority:
      1. ANTHROPIC_API_KEY set → claude_service  (Anthropic Claude — best quality)
      2. OPENROUTER_API_KEY set → openrouter_service  (free open-source: Qwen, DeepSeek, Llama)
      3. Neither set → ollama_service  (local Ollama fallback)

    Never call any service directly from pipeline.py — always go through this router.

    Returns:
        A service module exposing an async `generate(row, system_prompt, user_prompt)` function.
    """
    if settings.use_claude:
        from app.services import claude_service  # noqa: PLC0415

        logger.info("llm_router", selected="claude", model=settings.llm_model)
        return claude_service

    if settings.use_openrouter:
        from app.services import openrouter_service  # noqa: PLC0415

        logger.info("llm_router", selected="openrouter", model=settings.openrouter_model)
        return openrouter_service

    from app.services import ollama_service  # noqa: PLC0415

    logger.info("llm_router", selected="ollama", url=settings.ollama_url)
    return ollama_service
