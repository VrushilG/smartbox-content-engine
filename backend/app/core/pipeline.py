import asyncio
from collections.abc import AsyncGenerator

from app.config import settings
from app.core.dam_naming import generate_dam_filename
from app.models.output import GeneratedAsset
from app.models.product import ProductRow
from app.prompts.category_tones import CATEGORY_TONES
from app.prompts.content_prompt import build_prompt
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.prompts.video_template import build_video_prompt
from app.services import image_service, supabase_service, video_service
from app.services.llm_router import get_service
from app.utils.exceptions import PipelineError
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Step 1 — Text generation
# ---------------------------------------------------------------------------

async def _run_text_step(
    row: ProductRow,
    job_id: str,
    llm_service,
) -> GeneratedAsset:
    """Call the LLM to generate video script, voiceover, image prompt, video prompt,
    product description, and hashtags for one product row.

    To change the text generation prompt, edit:
      - app/prompts/system_prompt.py  (controls JSON spec + brand voice rules)
      - app/prompts/content_prompt.py (builds the per-row user message)
      - app/prompts/category_tones.py (per-category tone guidance injected into the prompt)

    To swap the LLM provider, update:
      - app/services/llm_router.py  (priority: Claude → OpenRouter → Ollama)
    """
    tone = CATEGORY_TONES.get(row.category.value, "warm and engaging")
    user_prompt = build_prompt(row, tone)

    asset = await llm_service.generate(
        row=row,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # DAM filename is derived deterministically from the text-gen output
    asset.dam_filename = generate_dam_filename(
        product_id=row.id,
        category=row.category.value,
        locale=settings.default_locale,
    )

    logger.info("row_text_done", job_id=job_id, product_id=row.id)
    return asset


# ---------------------------------------------------------------------------
# Step 2 — Image generation
# ---------------------------------------------------------------------------

async def _run_image_step(
    asset: GeneratedAsset,
    row: ProductRow,
    job_id: str,
) -> tuple[str, str]:
    """Generate a hero image for one product row.

    Uses the image_prompt field produced by the LLM in Step 1 as the generation
    prompt. Falls back to a minimal prompt if image_prompt is empty.

    Returns (image_url, image_status) where status is "done" | "failed" | "skipped".

    To change image generation:
      - app/services/image_service.py   (HuggingFace FLUX primary, Pollinations fallback)
      - The image_prompt instructions live in app/prompts/system_prompt.py
    """
    image_prompt = (
        asset.image_prompt
        or f"{row.name} in {row.location}, cinematic photography"
    )

    image_url, image_status = await image_service.generate_image(image_prompt, row.id)

    # Upload to Supabase Storage when configured
    if image_status == "done" and settings.use_supabase:
        local_path = image_service.STATIC_IMAGES_DIR / f"{row.id}.jpg"
        if local_path.exists():
            image_bytes = local_path.read_bytes()
            supabase_url = await supabase_service.upload_image(job_id, row.id, image_bytes)
            if supabase_url:
                image_url = supabase_url

    logger.info(
        "row_image_done",
        job_id=job_id,
        product_id=row.id,
        status=image_status,
        url=image_url[:60] if image_url else "",
    )
    return image_url, image_status


# ---------------------------------------------------------------------------
# Step 3 — Video generation
# ---------------------------------------------------------------------------

async def _run_video_step(
    asset: GeneratedAsset,
    row: ProductRow,
    job_id: str,
) -> tuple[str, str, str]:
    """Generate a short video clip for one product row.

    Uses the video_prompt field produced by the LLM in Step 1.  This is the
    prompt you want to tweak if the generated videos don't match the desired
    visual style — edit the video_prompt field instructions in:
      - app/prompts/system_prompt.py   (the JSON spec that controls what the LLM generates)

    Falls back to a generic cinematic description when video_prompt is empty.

    Returns (video_url, video_status, video_error) where status is "done" | "failed" | "skipped".

    To change the video provider or model:
      - app/services/video_service.py  (Google Veo → Fal.ai Wan → Replicate cascade)
    """
    scene = (
        asset.video_prompt
        or f"people enjoying {row.name}, warm atmosphere, natural setting"
    )
    environment_hint = (
        f"a scenic location near {row.location}" if row.location else "a scenic outdoor location"
    )
    video_prompt = build_video_prompt(scene, environment_hint)
    logger.debug("video_prompt_composed", product_id=row.id, prompt=video_prompt)

    video_url, video_status, video_error = await video_service.generate_video(
        video_prompt, product_id=row.id
    )

    # Upload to Supabase Storage when configured
    if video_status == "done" and settings.use_supabase:
        local_path = video_service.STATIC_VIDEOS_DIR / f"{row.id}.mp4"
        if local_path.exists():
            video_bytes = local_path.read_bytes()
            supabase_video_url = await supabase_service.upload_video(
                job_id, row.id, video_bytes
            )
            if supabase_video_url:
                video_url = supabase_video_url

    logger.info(
        "row_video_done",
        job_id=job_id,
        product_id=row.id,
        status=video_status,
        url=video_url[:60] if video_url else "",
        error=video_error or None,
    )
    return video_url, video_status, video_error


# ---------------------------------------------------------------------------
# Orchestrator — called by routes.py /process endpoint
# ---------------------------------------------------------------------------

async def process_csv(
    rows: list[ProductRow],
    job_id: str,
    user_id: str = "",
) -> AsyncGenerator[tuple[str, dict], None]:
    """Process a list of ProductRow objects and yield SSE event tuples.

    Per-row event sequence:
      1. row_started           — processing begins
      2. row_text_done         — LLM text generation complete
      3. row_image_generating  — image generation in progress
      4. row_image_done        — image ready (or failed/skipped)
      5. row_video_generating  — video generation in progress (may take 1–4 min)
      6. row_video_done        — video ready (or failed/skipped)
      7. row_done              — complete asset with all URLs

    On any media failure: logs a warning, sets status to "failed", continues.
    On LLM failure: yields row_error and moves to the next row.
    """
    llm_service = get_service()
    logger.info(
        "pipeline_started",
        job_id=job_id,
        row_count=len(rows),
        llm_service=type(llm_service).__name__,
    )

    await supabase_service.save_job(job_id, len(rows), user_id=user_id)

    semaphore = asyncio.Semaphore(settings.row_concurrency)
    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()  # sentinel to signal all rows finished

    async def _process_one(row: ProductRow) -> None:
        async with semaphore:
            await queue.put(("row_started", {"job_id": job_id, "product_id": row.id, "name": row.name}))
            logger.info("row_started", job_id=job_id, product_id=row.id)

            # ---- Step 1: Text ----
            try:
                asset = await _run_text_step(row, job_id, llm_service)
                await queue.put(("row_text_done", {
                    "job_id": job_id,
                    "product_id": row.id,
                    "asset": asset.model_dump(),
                }))
            except PipelineError as exc:
                logger.error("row_error", job_id=job_id, product_id=row.id, error=str(exc))
                await queue.put(("row_error", {"job_id": job_id, "product_id": row.id, "error": str(exc)}))
                return
            except Exception as exc:
                logger.error("row_unexpected_error", job_id=job_id, product_id=row.id, error=str(exc))
                await queue.put(("row_error", {
                    "job_id": job_id,
                    "product_id": row.id,
                    "error": f"Text generation failed: {exc}",
                }))
                return

            # ---- Step 2: Image ----
            logger.info("row_image_generating", job_id=job_id, product_id=row.id)
            await queue.put(("row_image_generating", {"job_id": job_id, "product_id": row.id}))

            image_url, image_status = await _run_image_step(asset, row, job_id)
            asset.image_url = image_url
            asset.image_status = image_status
            await queue.put(("row_image_done", {
                "job_id": job_id,
                "product_id": row.id,
                "image_url": image_url,
                "image_status": image_status,
            }))

            if image_status == "failed":
                logger.warning("row_stopped_image_failed", job_id=job_id, product_id=row.id)
                await queue.put(("row_error", {"job_id": job_id, "product_id": row.id, "error": "Image generation failed — skipping video to avoid further charges"}))
                return

            # ---- Step 3: Video ----
            logger.info("row_video_generating", job_id=job_id, product_id=row.id)
            await queue.put(("row_video_generating", {"job_id": job_id, "product_id": row.id}))

            video_url, video_status, video_error = await _run_video_step(asset, row, job_id)
            asset.video_url = video_url
            asset.video_status = video_status
            asset.video_error = video_error
            await queue.put(("row_video_done", {
                "job_id": job_id,
                "product_id": row.id,
                "video_url": video_url,
                "video_status": video_status,
                "video_error": video_error,
            }))

            if video_status == "failed":
                logger.warning("row_stopped_video_failed", job_id=job_id, product_id=row.id, reason=video_error)
                await queue.put(("row_error", {"job_id": job_id, "product_id": row.id, "error": f"Video generation failed — {video_error}"}))
                return

            # ---- Step 4: Persist to Supabase (no-op if not configured) ----
            await supabase_service.save_asset(job_id, asset, name=row.name, user_id=user_id)

            # ---- Step 5: Final event with complete asset ----
            logger.info(
                "row_done",
                job_id=job_id,
                product_id=row.id,
                dam_filename=asset.dam_filename,
                image_status=image_status,
                video_status=video_status,
            )
            await queue.put(("row_done", {"job_id": job_id, "product_id": row.id, "asset": asset.model_dump()}))

    async def _run_all() -> None:
        await asyncio.gather(*[_process_one(row) for row in rows], return_exceptions=True)
        await queue.put(_DONE)

    asyncio.create_task(_run_all())

    while True:
        item = await queue.get()
        if item is _DONE:
            break
        yield item
