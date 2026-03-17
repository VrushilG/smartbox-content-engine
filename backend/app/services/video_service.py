"""video_service.py — generate real videos from a text prompt.

Provider priority:
  1. Vertex AI Veo 3 Fast  — PRIMARY (VERTEXAI_PROJECT + GOOGLE_APPLICATION_CREDENTIALS)
       Model: veo-3-fast, 5-second output, 16:9 aspect ratio
  2. Fal.ai Wan 2.1        — fallback (FAL_API_KEY)
  3. Replicate Wan 2.1     — second fallback (REPLICATE_API_KEY)
  4. Skipped               — if no provider is configured.

Videos are saved locally to app/static/videos/{product_id}.mp4
and served at /static/videos/{product_id}.mp4.
"""

import asyncio
import os
import random
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Veo has strict per-minute quotas (typically 1–2 QPM).
# Serialise all Veo calls so parallel row processing doesn't trigger
# RESOURCE_EXHAUSTED / 429 errors on Railway's low-latency network.
_VEO_SEMAPHORE = asyncio.Semaphore(1)


def _get_vertex_client():
    """Return a Vertex AI genai.Client using a randomly chosen configured project.

    When multiple projects are configured (VERTEXAI_PROJECT + VERTEXAI_PROJECT_2),
    calls are distributed randomly to balance quota usage across both.
    """
    from google import genai  # noqa: PLC0415

    projects = settings.vertex_projects
    if not projects:
        raise RuntimeError("No Vertex AI project configured — set VERTEXAI_PROJECT")
    cfg = random.choice(projects)
    if cfg["credentials"]:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cfg["credentials"]
    logger.debug("vertex_client_selected", project=cfg["project"])
    return genai.Client(vertexai=True, project=cfg["project"], location=cfg["location"])

STATIC_VIDEOS_DIR = Path(__file__).parent.parent / "static" / "videos"

FAL_MODEL = "fal-ai/wan-t2v"
REPLICATE_MODEL = "wavespeedai/wan-2.1-t2v-480p"
VERTEX_VEO_MODEL = "veo-3.1-fast-generate-001"


def _ensure_static_dir() -> None:
    STATIC_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


async def generate_video(prompt: str, product_id: str = "") -> tuple[str, str, str]:
    """Generate a short video clip from a visual prompt.

    Returns (video_url, status, error_reason).
    status is "done", "failed", or "skipped".

    Uses the first configured provider only — no fallback cascade to avoid
    unexpected charges if the primary provider fails.

    Provider priority (first configured wins):
      1. Vertex AI Veo 3 Fast — if VERTEXAI_PROJECT is set (PRIMARY).
      2. Fal.ai Wan           — if FAL_API_KEY is set.
      3. Replicate Wan        — if REPLICATE_API_KEY is set.
    """
    if settings.use_vertexai and product_id:
        return await _generate_via_vertex_veo(prompt, product_id)

    if settings.use_fal:
        return await _generate_via_fal(prompt)

    if settings.use_replicate:
        return await _generate_via_replicate(prompt)

    logger.info("video_generate_skipped", reason="no_provider_configured")
    return "", "skipped", "No video provider configured — add VERTEXAI_PROJECT, FAL_API_KEY, or REPLICATE_API_KEY"


async def _generate_via_vertex_veo(prompt: str, product_id: str) -> tuple[str, str, str]:
    """Generate a 5-second video via Vertex AI Veo 3 Fast.

    Requires VERTEXAI_PROJECT env var and authentication via
    GOOGLE_APPLICATION_CREDENTIALS (service account JSON path) or
    `gcloud auth application-default login`.

    Polling pattern follows Google's reference:
      operation = client.models.generate_videos(...)
      while not operation.done: sleep + client.operations.get(operation)
      client.files.download(file=generated_video.video)
    """
    try:
        from google.genai import types as genai_types  # noqa: PLC0415
    except ImportError:
        logger.warning("google_genai_not_installed", hint="pip install google-genai")
        return "", "skipped", "google-genai package not installed"

    logger.info("video_generate_start", provider="vertex_veo", model=VERTEX_VEO_MODEL, product_id=product_id)
    async with _VEO_SEMAPHORE:
        try:
            client = _get_vertex_client()

            # Step 1: Submit generation
            operation = await asyncio.to_thread(
                client.models.generate_videos,
                model=VERTEX_VEO_MODEL,
                prompt=prompt,
                config=genai_types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    duration_seconds=4,  # Supported values: 4, 6, 8
                ),
            )
            logger.info("vertex_veo_operation_submitted", product_id=product_id, done=operation.done)

            # Step 2: Poll until done
            attempt = 0
            while not operation.done:
                await asyncio.sleep(15)
                operation = await asyncio.to_thread(client.operations.get, operation)
                attempt += 1
                logger.info("vertex_veo_poll", product_id=product_id, attempt=attempt, done=operation.done)
                if attempt >= 60:  # max 15 minutes
                    logger.warning("vertex_veo_timeout", product_id=product_id)
                    return "", "failed", "Generation timed out after 15 minutes"

            # Step 3: Check for API-level error (operation done but failed)
            op_error = getattr(operation, "error", None)
            if op_error:
                err_msg = getattr(op_error, "message", str(op_error))
                logger.error("vertex_veo_operation_error", product_id=product_id, error=err_msg)
                return "", "failed", err_msg[:200]

            # Step 4: Extract first generated video
            response = getattr(operation, "response", None)
            gen_videos = getattr(response, "generated_videos", None) if response else None
            if not gen_videos:
                logger.error("vertex_veo_no_generated_videos", product_id=product_id, response=str(response)[:300])
                return "", "failed", "No video returned by the API"

            generated_video = gen_videos[0]

            # Step 5: Extract video bytes and save to disk
            # On Vertex AI the SDK returns inline video_bytes directly (no files.download needed)
            video_bytes = getattr(generated_video.video, "video_bytes", None)
            if not video_bytes:
                logger.error("vertex_veo_empty_bytes", product_id=product_id)
                return "", "failed", "No video bytes in response"

            _ensure_static_dir()
            video_path = STATIC_VIDEOS_DIR / f"{product_id}.mp4"
            video_path.write_bytes(video_bytes)

            if not video_path.exists() or video_path.stat().st_size == 0:
                logger.error("vertex_veo_empty_file", product_id=product_id)
                return "", "failed", "Downloaded file was empty"

            size_kb = video_path.stat().st_size // 1024
            video_url = f"/static/videos/{product_id}.mp4"
            logger.info("video_generate_done", provider="vertex_veo", product_id=product_id, size_kb=size_kb, url=video_url)
            return video_url, "done", ""

        except Exception as exc:
            err_str = str(exc)
            if "quota" in err_str.lower() or "rate" in err_str.lower() or "429" in err_str:
                reason = f"Veo rate limit hit — {err_str[:150]}"
            elif "not found" in err_str.lower() or "404" in err_str:
                reason = f"Model not available — {err_str[:150]}"
            else:
                reason = err_str[:200]
            logger.warning("vertex_veo_failed", product_id=product_id, error=err_str[:500], reason=reason)
            return "", "failed", reason


async def _generate_via_fal(prompt: str) -> tuple[str, str, str]:
    """Generate video using Fal.ai's Wan model."""
    import fal_client  # noqa: PLC0415

    logger.info("video_generate_start", provider="fal", model=FAL_MODEL)
    os.environ.setdefault("FAL_KEY", settings.fal_api_key)

    try:
        handler = await fal_client.submit_async(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, text, watermark, distorted, static",
            },
        )
        result = await handler.get()
        video_url = result.get("video", {}).get("url", "")
        if not video_url:
            logger.error("fal_no_video_url", result=str(result)[:200])
            return "", "failed", "No video URL returned by Fal.ai"
        logger.info("video_generate_done", provider="fal", url=video_url[:80])
        return video_url, "done", ""
    except Exception as exc:
        err_str = str(exc)
        if "balance" in err_str.lower() or "locked" in err_str.lower():
            logger.warning("fal_billing_exhausted", hint="Top up at fal.ai/dashboard/billing")
            reason = "Fal.ai account balance exhausted"
        else:
            logger.error("fal_video_failed", error=err_str[:200])
            reason = err_str[:100]
        return "", "failed", reason


async def _generate_via_replicate(prompt: str) -> tuple[str, str, str]:
    """Generate video using Replicate's Wan 2.1 model."""
    import replicate  # noqa: PLC0415

    logger.info("video_generate_start", provider="replicate", model=REPLICATE_MODEL)
    os.environ.setdefault("REPLICATE_API_TOKEN", settings.replicate_api_key)

    try:
        output = await replicate.async_run(
            REPLICATE_MODEL,
            input={
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, text, watermark, distorted",
                "aspect_ratio": "16:9",
                "fast_mode": "Balanced",
            },
        )
        video_url = str(output) if output else ""
        if not video_url:
            logger.error("replicate_no_video_url")
            return "", "failed", "No video URL returned by Replicate"
        logger.info("video_generate_done", provider="replicate", url=video_url[:80])
        return video_url, "done", ""
    except Exception as exc:
        err_str = str(exc)
        if "insufficient credit" in err_str.lower() or "402" in err_str:
            logger.warning("replicate_billing_exhausted", hint="Add credit at replicate.com/account/billing")
            reason = "Insufficient Replicate credits"
        else:
            logger.error("replicate_video_failed", error=err_str[:200])
            reason = err_str[:100]
        return "", "failed", reason
