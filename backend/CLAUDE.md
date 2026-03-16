# Backend — Smartbox Content Engine

## Stack
- Python 3.11
- FastAPI with uvicorn (async)
- Anthropic Python SDK
- Pydantic v2 for all models
- pandas for CSV parsing
- python-dotenv for env management
- pytest for tests
- ruff + black for linting

## Architecture
- app/main.py       — creates FastAPI instance, mounts router, serves frontend static files
- app/config.py     — single source of truth for all settings, never import os.environ directly elsewhere
- app/api/routes.py — all HTTP routes: POST /process, GET /health, GET /status/{job_id}
- app/core/         — pure business logic, no HTTP dependencies
- app/services/     — external API calls only (Claude, Ollama)
- app/models/       — Pydantic schemas only, no logic
- app/prompts/      — prompt strings and brand tone config only
- app/utils/        — shared helpers: logger, SSE formatter, exceptions

## Coding conventions
- Use async/await throughout — no sync blocking calls
- All route handlers must have type annotations
- All Pydantic models use model_config = ConfigDict(strict=True)
- Use structlog via utils/logger.py — never use print() statements
- SSE events must use utils/sse.py formatter — never construct raw SSE strings inline
- Raise custom exceptions from utils/exceptions.py — never raise bare Exception
- Category enum lives in models/product.py — import from there, never redefine

## LLM routing rule
IMPORTANT: llm_router.py checks for ANTHROPIC_API_KEY in config.
- If key present → use claude_service.py (Anthropic SDK)
- If key missing → use ollama_service.py (local fallback)
Never bypass llm_router.py to call either service directly from pipeline.py

## DAM filename format
PROD-{id}_{CATEGORY}_{LOCALE}_{YYYYMMDD}.mp4
Generated exclusively by core/dam_naming.py — never construct this string elsewhere.

## Testing rules
- Every function in core/ must have a corresponding test in tests/
- Use pytest fixtures for sample ProductRow data — defined in tests/conftest.py
- Mock all external API calls in tests — never make real API calls in tests
- Run: pytest tests/ -v --tb=short
