import json

import httpx

from app.config import settings
from app.models.output import GeneratedAsset
from app.models.product import ProductRow
from app.utils.exceptions import LLMError
from app.utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_MODEL = "llama3"


async def generate(
    row: ProductRow,
    system_prompt: str,
    user_prompt: str,
) -> GeneratedAsset:
    """Generate content assets using a local Ollama instance.

    Same interface as claude_service.generate. Used as a fallback when
    neither ANTHROPIC_API_KEY nor OPENROUTER_API_KEY is configured.

    Args:
        row: The product row being processed.
        system_prompt: The system-level brand voice instructions.
        user_prompt: The per-row user message built by content_prompt.py.

    Returns:
        A GeneratedAsset populated with LLM output (dam_filename/image_url/video_url set by pipeline).

    Raises:
        LLMError: If the Ollama request fails or the response cannot be parsed.
    """
    url = f"{settings.ollama_url.rstrip('/')}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    logger.info("ollama_generate_start", product_id=row.id, url=url, model=OLLAMA_MODEL)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMError(f"Ollama request failed for product {row.id}: {exc}") from exc

    body = response.json()
    raw_text = body.get("message", {}).get("content", "").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"Ollama returned non-JSON for product {row.id}: {raw_text[:200]}"
        ) from exc

    logger.info("ollama_generate_done", product_id=row.id)

    return GeneratedAsset(
        product_id=row.id,
        video_script=data.get("video_script", ""),
        voiceover_copy=data.get("voiceover_copy", ""),
        product_description=data.get("product_description", ""),
        image_prompt=data.get("image_prompt", ""),
        video_prompt=data.get("video_prompt", ""),
        hashtags=data.get("hashtags", []),
        dam_filename="",
    )
