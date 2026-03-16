import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_process_returns_422_on_empty_file():
    csv_content = b""
    files = {"file": ("empty.csv", io.BytesIO(csv_content), "text/csv")}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/process", files=files)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_process_returns_422_on_missing_columns():
    csv_content = b"id,name\n001,Spa\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content), "text/csv")}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/process", files=files)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_process_streams_sse_events():
    from app.models.output import GeneratedAsset

    valid_csv = (
        b"id,name,location,price,category,key_selling_point\n"
        b"001,Spa Escape,Wicklow,149,wellness,Mountain retreat\n"
    )

    mock_asset = GeneratedAsset(
        product_id="001",
        video_script="Script here",
        voiceover_copy="Voiceover here",
        image_prompt="Image prompt here, golden hour, cinematic",
        video_prompt="Slow aerial shot over spa, golden light, mountain mist",
        hashtags=["wellness", "ireland"],
        dam_filename="PROD-001_WELLNESS_IE_20240101.mp4",
        image_url="https://image.pollinations.ai/prompt/test?model=flux",
        image_status="done",
    )

    async def fake_process_csv(rows, job_id, **kwargs):
        for row in rows:
            yield "row_started", {"job_id": job_id, "product_id": row.id, "name": row.name}
            yield "row_done", {"job_id": job_id, "product_id": row.id, "asset": mock_asset.model_dump()}

    files = {"file": ("products.csv", io.BytesIO(valid_csv), "text/csv")}
    with patch("app.api.routes.process_csv", side_effect=fake_process_csv):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/process", files=files)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "job_started" in body
    assert "row_started" in body or "row_done" in body


@pytest.mark.asyncio
async def test_status_returns_404_for_unknown_job():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status/nonexistent-job-id")
    assert response.status_code == 404
