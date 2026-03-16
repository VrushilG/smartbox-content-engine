import json

import anthropic

from app.config import settings
from app.models.output import GeneratedAsset
from app.models.product import ProductRow
from app.utils.exceptions import LLMError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def generate(
    row: ProductRow,
    system_prompt: str,
    user_prompt: str,
) -> GeneratedAsset:
    """Generate content assets for a product using the Anthropic Claude API.

    Args:
        row: The product row being processed.
        system_prompt: The system-level brand voice instructions.
        user_prompt: The per-row user message built by content_prompt.py.

    Returns:
        A GeneratedAsset populated with LLM output (dam_filename/image_url/video_url set by pipeline).

    Raises:
        LLMError: If the API call fails or the response cannot be parsed.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    logger.info("claude_generate_start", product_id=row.id, model=settings.llm_model)

    try:
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as exc:
        raise LLMError(f"Claude API error for product {row.id}: {exc}") from exc

    raw_text = message.content[0].text.strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"Claude returned non-JSON for product {row.id}: {raw_text[:200]}"
        ) from exc

    logger.info("claude_generate_done", product_id=row.id)

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
