"""
generate.py — Standalone generation endpoints

These endpoints let you call each generation step independently,
without running the full /process SSE pipeline. Useful for testing
individual steps or building custom workflows.

Endpoints:
  POST /generate/text   — CSV → JSON array of text assets (script, voiceover, prompts, etc.)
  POST /generate/image  — image prompt → image URL
  POST /generate/video  — video prompt → video URL
"""

from fastapi import APIRouter, Header, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.core.csv_parser import parse_csv
from app.core.dam_naming import generate_dam_filename
from app.prompts.category_tones import CATEGORY_TONES
from app.prompts.content_prompt import build_prompt
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services import image_service, video_service
from app.services.llm_router import get_service
from app.utils.exceptions import CSVValidationError
from app.utils.logger import get_logger

router = APIRouter(prefix="/generate", tags=["generate"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class ImageRequest(BaseModel):
    product_id: str
    image_prompt: str


class VideoRequest(BaseModel):
    product_id: str
    video_prompt: str


# ---------------------------------------------------------------------------
# POST /generate/text
# ---------------------------------------------------------------------------

@router.post("/text")
async def generate_text(
    file: UploadFile,
    x_user_id: str = Header(default=""),
) -> list[dict]:
    """Generate text content for every row in an uploaded CSV.

    Runs the LLM step only — no image or video generation.
    Returns a JSON array of objects, one per CSV row, containing:
    video_script, voiceover_copy, product_description, image_prompt,
    video_prompt, hashtags, dam_filename.

    To modify what the LLM generates or how it writes, edit:
      - app/prompts/system_prompt.py   (JSON spec + brand voice rules)
      - app/prompts/content_prompt.py  (per-row user message)
      - app/prompts/category_tones.py  (per-category tone guidance)
    """
    try:
        rows = await parse_csv(file)
    except CSVValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    service = get_service()
    logger.info("generate_text_started", row_count=len(rows), llm=type(service).__name__)

    results = []
    for row in rows:
        tone = CATEGORY_TONES.get(row.category.value, "warm and engaging")
        user_prompt = build_prompt(row, tone)
        asset = await service.generate(
            row=row,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        asset.dam_filename = generate_dam_filename(
            product_id=row.id,
            category=row.category.value,
            locale=settings.default_locale,
        )
        results.append(asset.model_dump())

    logger.info("generate_text_done", row_count=len(results))
    return results


# ---------------------------------------------------------------------------
# POST /generate/image
# ---------------------------------------------------------------------------

@router.post("/image")
async def generate_image(body: ImageRequest) -> dict:
    """Generate a hero image from an image prompt.

    To change the image provider or model, edit:
      - app/services/image_service.py
    To change how image prompts are written by the LLM, edit:
      - app/prompts/system_prompt.py  (the image_prompt field spec)
    """
    logger.info("generate_image_started", product_id=body.product_id)

    image_url, image_status = await image_service.generate_image(
        body.image_prompt, body.product_id
    )

    logger.info(
        "generate_image_done",
        product_id=body.product_id,
        status=image_status,
        url=image_url[:60] if image_url else "",
    )
    return {
        "product_id": body.product_id,
        "image_url": image_url,
        "image_status": image_status,
    }


# ---------------------------------------------------------------------------
# POST /generate/video
# ---------------------------------------------------------------------------

@router.post("/video")
async def generate_video(body: VideoRequest) -> dict:
    """Generate a short video clip from a video prompt.

    May take 1–4 minutes depending on the configured provider.
    Returns as soon as the video is ready (synchronous, not streamed).

    To change the video provider or model, edit:
      - app/services/video_service.py  (Google Veo → Fal.ai → Replicate cascade)
    To change how video prompts are written by the LLM, edit:
      - app/prompts/system_prompt.py  (the video_prompt field spec)
    """
    logger.info("generate_video_started", product_id=body.product_id)

    video_url, video_status = await video_service.generate_video(
        body.video_prompt, product_id=body.product_id
    )

    logger.info(
        "generate_video_done",
        product_id=body.product_id,
        status=video_status,
        url=video_url[:60] if video_url else "",
    )
    return {
        "product_id": body.product_id,
        "video_url": video_url,
        "video_status": video_status,
    }
