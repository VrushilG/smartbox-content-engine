import json

from openai import AsyncOpenAI

from app.config import settings
from app.models.output import GeneratedAsset
from app.models.product import ProductRow
from app.utils.exceptions import LLMError
from app.utils.logger import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.openrouter_api_key,
        default_headers={
            "HTTP-Referer": "https://smartbox.com",
            "X-Title": "Smartbox Content Engine",
        },
    )


async def generate(
    row: ProductRow,
    system_prompt: str,
    user_prompt: str,
) -> GeneratedAsset:
    """Generate content assets via OpenRouter using free open-source models.

    Supports any OpenRouter model. Defaults to Qwen 2.5 72B (Alibaba, free tier).
    Other recommended free models:
      - deepseek/deepseek-chat-v3-0324:free  (DeepSeek V3)
      - meta-llama/llama-3.3-70b:free        (Meta Llama 3.3)
      - qwen/qwen3-coder-480b:free           (Qwen3 Coder)

    Args:
        row: The product row being processed.
        system_prompt: The system-level brand voice instructions.
        user_prompt: The per-row user message built by content_prompt.py.

    Returns:
        A GeneratedAsset populated with LLM output (dam_filename/image_url/video_url set by pipeline).

    Raises:
        LLMError: If the API call fails or the response cannot be parsed.
    """
    client = _make_client()
    model = settings.openrouter_model
    logger.info("openrouter_generate_start", product_id=row.id, model=model)

    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise LLMError(f"OpenRouter API error for product {row.id}: {exc}") from exc

    raw_text = (response.choices[0].message.content or "").strip()

    # Strip markdown code fences if model wraps output in ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```", 2)[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.rstrip("` \n")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"OpenRouter returned non-JSON for product {row.id}: {raw_text[:200]}"
        ) from exc

    logger.info("openrouter_generate_done", product_id=row.id, model=model)

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
