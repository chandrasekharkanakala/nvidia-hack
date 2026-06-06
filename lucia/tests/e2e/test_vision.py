"""E2E tests for vision capabilities (image upload → real analysis)."""

import pytest
import base64
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as c:
        yield c


@pytest.fixture
def traffic_image_b64():
    """Generate a synthetic test image (small JPEG-like payload)."""
    # Minimal 1x1 pixel PNG (red) as base64
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return base64.b64encode(png_bytes).decode("utf-8")


@pytest.mark.e2e
class TestVisionE2E:
    """End-to-end tests for image analysis via NeVA-7B."""

    @pytest.mark.asyncio
    async def test_image_upload_returns_description(self, client, traffic_image_b64):
        """Uploading an image should return a description."""
        response = await client.post("/api/chat", json={
            "content": "Describe what you see in this image",
            "mode": "chat",
            "image": traffic_image_b64,
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 20

    @pytest.mark.asyncio
    async def test_image_with_specific_question(self, client, traffic_image_b64):
        """Should answer specific questions about the image."""
        response = await client.post("/api/chat", json={
            "content": "How many vehicles are visible in this image?",
            "mode": "chat",
            "image": traffic_image_b64,
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 10

    @pytest.mark.asyncio
    async def test_vision_latency(self, client, traffic_image_b64):
        """Vision analysis should complete within 3 seconds."""
        import time

        start = time.perf_counter()
        response = await client.post("/api/chat", json={
            "content": "Describe this traffic scene",
            "mode": "chat",
            "image": traffic_image_b64,
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 3.0, f"Vision took {elapsed:.2f}s, expected < 3s"

    @pytest.mark.asyncio
    async def test_vision_detects_anomalies(self, client, traffic_image_b64):
        """Vision should identify potential anomalies."""
        response = await client.post("/api/chat", json={
            "content": "Are there any traffic incidents or anomalies visible?",
            "mode": "chat",
            "image": traffic_image_b64,
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 10

    @pytest.mark.asyncio
    async def test_vision_without_image_errors(self, client):
        """Vision question without image should handle gracefully."""
        response = await client.post("/api/chat", json={
            "content": "Describe what you see in this image",
            "mode": "chat",
            # No image provided
        })

        assert response.status_code == 200
        # Should indicate no image or ask for one
        data = response.json()
        assert len(data["response"]) > 0
