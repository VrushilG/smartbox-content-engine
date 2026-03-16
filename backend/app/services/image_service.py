import asyncio
import random
from pathlib import Path

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_vertex_client():
    """Return a Vertex AI genai.Client using a randomly chosen configured project.

    When multiple projects are configured (VERTEXAI_PROJECT + VERTEXAI_PROJECT_2),
    calls are distributed randomly to balance quota usage across both.
    """
    from google import genai  # noqa: PLC0415
    import os  # noqa: PLC0415

    projects = settings.vertex_projects
    if not projects:
        raise RuntimeError("No Vertex AI project configured — set VERTEXAI_PROJECT")
    cfg = random.choice(projects)
    if cfg["credentials"]:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cfg["credentials"]
    logger.debug("vertex_client_selected", project=cfg["project"])
    return genai.Client(vertexai=True, project=cfg["project"], location=cfg["location"])

# Local directory for saved images
STATIC_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images"


def _ensure_static_dir() -> None:
    """Create the static/images directory if it doesn't exist."""
    STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def _generate_via_vertex_imagen(prompt: str, product_id: str) -> tuple[str, str]:
    """Generate image via Vertex AI Imagen 4 Fast (PRIMARY).

    Requires VERTEXAI_PROJECT env var and authentication via
    GOOGLE_APPLICATION_CREDENTIALS (service account JSON path) or
    `gcloud auth application-default login`.
    """
    try:
        from google.genai import types as genai_types  # noqa: PLC0415
    except ImportError:
        logger.warning("google_genai_not_installed_for_vertex_imagen")
        return "", "failed"

    logger.info("image_generate_start", provider="vertex_imagen", product_id=product_id)
    try:
        client = _get_vertex_client()
        response = await asyncio.to_thread(
            client.models.generate_images,
            model="imagen-4.0-fast-generate-001",
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        _ensure_static_dir()
        image_path = STATIC_IMAGES_DIR / f"{product_id}.jpg"
        image_path.write_bytes(image_bytes)
        image_url = f"/static/images/{product_id}.jpg"
        logger.info("image_generate_done", provider="vertex_imagen", product_id=product_id, url=image_url)
        return image_url, "done"
    except Exception as exc:
        logger.warning("vertex_imagen_failed", product_id=product_id, error=str(exc)[:300])
        return "", "failed"


async def _generate_via_fal(prompt: str, product_id: str) -> tuple[str, str]:
    """Generate an image via Fal.ai FLUX Schnell (reuses FAL_API_KEY).

    Downloads the image and saves it to static/images/{product_id}.jpg.
    """
    import os  # noqa: PLC0415

    import fal_client  # noqa: PLC0415

    os.environ.setdefault("FAL_KEY", settings.fal_api_key)
    logger.info("image_generate_start", provider="fal", product_id=product_id)
    try:
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_16_9",
                "num_inference_steps": 4,
                "num_images": 1,
            },
        )
        result = await handler.get()
        images = result.get("images", [])
        if not images:
            logger.error("fal_image_no_images", product_id=product_id)
            return "", "failed"

        image_url_remote = images[0].get("url", "")
        if not image_url_remote:
            logger.error("fal_image_empty_url", product_id=product_id)
            return "", "failed"

        # Download and save locally
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(image_url_remote)
            resp.raise_for_status()
            _ensure_static_dir()
            image_path = STATIC_IMAGES_DIR / f"{product_id}.jpg"
            image_path.write_bytes(resp.content)

        image_url = f"/static/images/{product_id}.jpg"
        logger.info("image_generate_done", provider="fal", product_id=product_id, url=image_url)
        return image_url, "done"

    except Exception as exc:
        logger.warning("fal_image_failed", product_id=product_id, error=str(exc)[:200])
        return "", "failed"


async def generate_image(prompt: str, product_id: str) -> tuple[str, str]:
    """Generate an image from a text prompt and save it locally.

    Tries providers in order:
      1. Vertex AI Imagen 4 Fast — if vertexai_project is set (PRIMARY).
      2. Fal.ai FLUX Schnell     — if fal_api_key is set.
      3. Lorem Picsum            — free stock photo, no key (final fallback).

    Args:
        prompt: The visual prompt string (from GeneratedAsset.image_prompt).
        product_id: Used as the filename when saving generated bytes to disk.

    Returns:
        A tuple of (image_url: str, status: str).
        status is "done" on success or "failed" if all providers fail.
    """
    # ---- Primary: Vertex AI Imagen 4 Fast ----
    if settings.use_vertexai:
        url, status = await _generate_via_vertex_imagen(prompt, product_id)
        if status == "done":
            return url, status
        logger.warning("vertex_imagen_failed_trying_fal", product_id=product_id)

    # ---- Fallback 1: Fal.ai FLUX Schnell ----
    if settings.use_fal:
        url, status = await _generate_via_fal(prompt, product_id)
        if status == "done":
            return url, status
        logger.warning("fal_image_failed_trying_picsum", product_id=product_id)

    # ---- Final fallback: Lorem Picsum (free, no key, deterministic per product) ----
    logger.info("image_generate_start", provider="picsum", product_id=product_id)
    try:
        picsum_url = f"https://picsum.photos/seed/{product_id}/1024/576"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(picsum_url)
            resp.raise_for_status()
            if resp.content:
                _ensure_static_dir()
                image_path = STATIC_IMAGES_DIR / f"{product_id}.jpg"
                image_path.write_bytes(resp.content)
                image_url = f"/static/images/{product_id}.jpg"
                logger.info("image_generate_done", provider="picsum", product_id=product_id, url=image_url)
                return image_url, "done"
    except Exception as exc:
        logger.warning("picsum_image_failed", product_id=product_id, error=str(exc)[:200])

    return "", "failed"
