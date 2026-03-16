"""supabase_service.py — optional Supabase persistence layer.

Saves job metadata and generated assets to Supabase.
Uploads product images to Supabase Storage bucket 'product-images'.

Requires env vars: SUPABASE_URL, SUPABASE_SERVICE_KEY
If not set, all operations are no-ops — the pipeline continues without persistence.
"""

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    try:
        from supabase import create_client  # noqa: PLC0415
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
        return _client
    except Exception as exc:
        logger.warning("supabase_init_failed", error=str(exc))
        return None


async def save_job(job_id: str, rows_total: int, user_id: str = "") -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.table("content_jobs").upsert({
            "id": job_id,
            "rows_total": rows_total,
            "status": "running",
            "user_id": user_id,
        }).execute()
        logger.info("supabase_job_saved", job_id=job_id, user_id=user_id or "anonymous")
    except Exception as exc:
        logger.warning("supabase_save_job_failed", error=str(exc))


async def complete_job(job_id: str, rows_done: int) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.table("content_jobs").update({
            "status": "complete",
            "rows_done": rows_done,
        }).eq("id", job_id).execute()
    except Exception as exc:
        logger.warning("supabase_complete_job_failed", error=str(exc))


async def save_asset(job_id: str, asset, name: str = "", user_id: str = "") -> None:
    """Save a GeneratedAsset to the content_assets table."""
    client = _get_client()
    if not client:
        return
    try:
        client.table("content_assets").upsert({
            "job_id": job_id,
            "product_id": asset.product_id,
            "name": name,
            "user_id": user_id,
            "video_script": asset.video_script,
            "voiceover_copy": asset.voiceover_copy,
            "product_description": asset.product_description,
            "image_prompt": asset.image_prompt,
            "video_prompt": asset.video_prompt,
            "hashtags": asset.hashtags,
            "dam_filename": asset.dam_filename,
            "image_url": asset.image_url,
            "video_url": asset.video_url,
            "image_status": asset.image_status,
            "video_status": asset.video_status,
        }).execute()
        logger.info("supabase_asset_saved", product_id=asset.product_id)
    except Exception as exc:
        logger.warning("supabase_save_asset_failed", error=str(exc))


async def upload_image(job_id: str, product_id: str, image_bytes: bytes) -> str:
    """Upload image bytes to Supabase Storage and return the public URL.

    Returns empty string if Supabase is not configured or upload fails.
    """
    client = _get_client()
    if not client:
        return ""
    try:
        path = f"{job_id}/{product_id}.jpg"
        client.storage.from_("product-images").upload(
            path,
            image_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
        public_url = client.storage.from_("product-images").get_public_url(path)
        logger.info("supabase_image_uploaded", product_id=product_id, url=public_url[:80])
        return public_url
    except Exception as exc:
        logger.warning("supabase_upload_image_failed", error=str(exc))
        return ""


async def upload_video(job_id: str, product_id: str, video_bytes: bytes) -> str:
    """Upload video bytes to Supabase Storage bucket 'product-videos'.

    Returns the public URL, or empty string on failure.
    """
    client = _get_client()
    if not client:
        return ""
    try:
        path = f"{job_id}/{product_id}.mp4"
        client.storage.from_("product-videos").upload(
            path,
            video_bytes,
            {"content-type": "video/mp4", "upsert": "true"},
        )
        public_url = client.storage.from_("product-videos").get_public_url(path)
        logger.info("supabase_video_uploaded", product_id=product_id, url=public_url[:80])
        return public_url
    except Exception as exc:
        logger.warning("supabase_upload_video_failed", error=str(exc))
        return ""


async def delete_asset(product_id: str, user_id: str = "") -> None:
    """Delete a content_asset row plus its storage objects (image + video)."""
    client = _get_client()
    if not client:
        return
    try:
        # Fetch the asset first to get job_id for storage paths
        q = client.table("content_assets").select("job_id").eq("product_id", product_id)
        if user_id:
            q = q.eq("user_id", user_id)
        result = q.execute()
        rows = result.data or []

        if rows:
            job_id = rows[0].get("job_id", "")
            if job_id:
                client.storage.from_("product-images").remove([f"{job_id}/{product_id}.jpg"])
                client.storage.from_("product-videos").remove([f"{job_id}/{product_id}.mp4"])

        # Delete from DB
        dq = client.table("content_assets").delete().eq("product_id", product_id)
        if user_id:
            dq = dq.eq("user_id", user_id)
        dq.execute()
        logger.info("supabase_asset_deleted", product_id=product_id)
    except Exception as exc:
        logger.warning("supabase_delete_asset_failed", error=str(exc))


async def get_user_history(user_id: str) -> list[dict]:
    """Return all content_assets rows for a given user, newest first."""
    client = _get_client()
    if not client:
        return []
    try:
        result = (
            client.table("content_assets")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning("supabase_get_history_failed", error=str(exc))
        return []
