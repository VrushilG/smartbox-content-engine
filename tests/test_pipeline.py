from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.output import GeneratedAsset
from app.models.product import ProductRow


def make_mock_asset(product_id: str) -> GeneratedAsset:
    return GeneratedAsset(
        product_id=product_id,
        video_script="Test script",
        voiceover_copy="Test voiceover",
        image_prompt="Test image prompt, golden hour, cinematic",
        video_prompt="Slow aerial shot, golden light, mountain spa",
        hashtags=["test", "smartbox"],
        dam_filename="",
    )


# ---- Helpers to patch both media services ----

def _patch_media(image_result=("https://test.img/flux.jpg", "done"), video_result=("", "skipped", "")):
    """Return a context manager that mocks both media services and Supabase calls."""
    import contextlib

    @contextlib.asynccontextmanager
    async def _ctx():
        with (
            patch("app.core.pipeline.image_service.generate_image", AsyncMock(return_value=image_result)),
            patch("app.core.pipeline.video_service.generate_video", AsyncMock(return_value=video_result)),
            patch("app.core.pipeline.supabase_service.upload_image", AsyncMock(return_value="")),
            patch("app.core.pipeline.supabase_service.upload_video", AsyncMock(return_value="")),
            patch("app.core.pipeline.supabase_service.save_job", AsyncMock()),
            patch("app.core.pipeline.supabase_service.save_asset", AsyncMock()),
        ):
            yield

    return _ctx()


@pytest.mark.asyncio
async def test_process_csv_yields_expected_events(sample_product_row: ProductRow):
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value=make_mock_asset(sample_product_row.id))

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media():
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    event_names = [e[0] for e in events]
    assert "row_started" in event_names
    assert "row_text_done" in event_names
    assert "row_image_done" in event_names
    assert "row_video_done" in event_names
    assert "row_done" in event_names


@pytest.mark.asyncio
async def test_process_csv_row_done_contains_full_asset(sample_product_row: ProductRow):
    mock_asset = make_mock_asset(sample_product_row.id)
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value=mock_asset)

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media(image_result=("https://img.test/photo.jpg", "done")):
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    row_done = next((d for n, d in events if n == "row_done"), None)
    assert row_done is not None
    asset = row_done["asset"]
    assert asset["product_id"] == sample_product_row.id
    assert asset["image_url"] == "https://img.test/photo.jpg"
    assert asset["image_status"] == "done"


@pytest.mark.asyncio
async def test_process_csv_dam_filename_set(sample_product_row: ProductRow):
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value=make_mock_asset(sample_product_row.id))

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media():
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    row_done = next((d for n, d in events if n == "row_done"), None)
    assert row_done is not None
    assert row_done["asset"]["dam_filename"].startswith("PROD-001_")
    assert row_done["asset"]["dam_filename"].endswith(".mp4")


@pytest.mark.asyncio
async def test_process_csv_llm_error_yields_row_error(sample_product_row: ProductRow):
    from app.utils.exceptions import LLMError

    mock_service = MagicMock()
    mock_service.generate = AsyncMock(side_effect=LLMError("API timeout"))

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media():
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    error_events = [(n, d) for n, d in events if n == "row_error"]
    assert len(error_events) == 1
    assert "API timeout" in error_events[0][1]["error"]


@pytest.mark.asyncio
async def test_process_csv_image_failure_stops_row(sample_product_row: ProductRow):
    """Image service failure should emit row_error and skip video generation."""
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value=make_mock_asset(sample_product_row.id))

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media(image_result=("", "failed")):
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    event_names = [n for n, _ in events]
    # Row should stop after image failure — no video step, no row_done
    assert "row_error" in event_names
    assert "row_video_generating" not in event_names
    assert "row_done" not in event_names


@pytest.mark.asyncio
async def test_process_csv_video_skipped(sample_product_row: ProductRow):
    """Video status should be 'skipped' when no video provider is configured."""
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value=make_mock_asset(sample_product_row.id))

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media(video_result=("", "skipped", "")):
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv([sample_product_row], job_id="test-job"):
                events.append((event_name, event_data))

    row_done = next((d for n, d in events if n == "row_done"), None)
    assert row_done is not None
    assert row_done["asset"]["video_status"] == "skipped"


@pytest.mark.asyncio
async def test_process_csv_multiple_rows(sample_product_rows: list[ProductRow]):
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(
        side_effect=[make_mock_asset(row.id) for row in sample_product_rows]
    )

    with patch("app.core.pipeline.get_service", return_value=mock_service):
        async with _patch_media():
            from app.core.pipeline import process_csv

            events = []
            async for event_name, event_data in process_csv(sample_product_rows, job_id="test-job"):
                events.append((event_name, event_data))

    row_done_count = sum(1 for n, _ in events if n == "row_done")
    assert row_done_count == len(sample_product_rows)
