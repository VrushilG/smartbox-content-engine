import json
import re

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


def _extract_json(raw: str) -> dict:
    """Extract a JSON object from a model response that may contain:
    - <think>...</think> reasoning blocks (DeepSeek R1, QwQ, etc.)
    - Markdown code fences (```json ... ```)
    - Explanatory preamble/postamble text

    Tries strict parse first, then progressively softer extraction.
    Raises ValueError if no valid JSON object is found.
    """
    # 1. Strip <think>...</think> blocks (reasoning models emit these)
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # 2. Extract content from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # 3. Try parsing as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Find the outermost {...} block in case there's preamble/postamble
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON object found in response: {raw[:300]}")


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
            max_tokens=1500,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        # Some models don't support response_format — retry without it
        logger.warning("openrouter_json_mode_unsupported", product_id=row.id, model=model, error=str(exc)[:100])
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc2:
            raise LLMError(f"OpenRouter API error for product {row.id}: {exc2}") from exc2

    raw_text = (response.choices[0].message.content or "").strip()
    logger.debug("openrouter_raw_response", product_id=row.id, preview=raw_text[:200])

    try:
        data = _extract_json(raw_text)
    except ValueError as exc:
        raise LLMError(f"OpenRouter returned non-JSON for product {row.id}: {exc}") from exc

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
