"""Unit tests for the vision tool."""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def sample_image_b64():
    """Minimal valid base64 image (1x1 red pixel PNG)."""
    # 1x1 red PNG
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return base64.b64encode(png_data).decode("utf-8")


@pytest.fixture
def mock_vision_llm_response():
    """Mock NeVA response with image description."""
    return MagicMock(
        choices=[MagicMock(message=MagicMock(
            content="The image shows a busy intersection with multiple vehicles including cars and buses. "
                    "There appears to be heavy traffic congestion. A traffic accident is visible in the "
                    "bottom-right corner involving two vehicles."
        ))],
    )


class TestVisionExecute:
    """Tests for vision.execute() image analysis."""

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_returns_description(self, mock_openai_cls, sample_image_b64, mock_vision_llm_response):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(return_value=mock_vision_llm_response)
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(image_base64=sample_image_b64, question="Describe this image")

        assert "description" in result
        assert len(result["description"]) > 0
        assert result["error"] is None

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_detects_objects(self, mock_openai_cls, sample_image_b64, mock_vision_llm_response):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(return_value=mock_vision_llm_response)
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(image_base64=sample_image_b64, question="What objects are visible?")

        assert "objects_detected" in result
        assert isinstance(result["objects_detected"], list)
        # Should detect vehicles from the description
        assert len(result["objects_detected"]) > 0

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_detects_anomalies(self, mock_openai_cls, sample_image_b64, mock_vision_llm_response):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(return_value=mock_vision_llm_response)
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(image_base64=sample_image_b64, question="Any issues?")

        assert "anomalies" in result
        assert isinstance(result["anomalies"], list)
        # Should detect accident from description keywords
        assert len(result["anomalies"]) > 0

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_handles_llm_failure(self, mock_openai_cls, sample_image_b64):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(side_effect=Exception("Model unavailable"))
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(image_base64=sample_image_b64, question="Describe")

        assert result.get("error") is not None

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_custom_question_passed_to_model(self, mock_openai_cls, sample_image_b64):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="I can see 5 pedestrians crossing."))]
            )
        )
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(
            image_base64=sample_image_b64,
            question="How many pedestrians are visible?"
        )

        assert "description" in result
        # Verify question was used in the API call
        call_args = llm.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        content_texts = str(messages)
        assert "pedestrian" in content_texts.lower()

    @pytest.mark.asyncio
    @patch("tools.vision.AsyncOpenAI")
    async def test_no_anomalies_for_normal_scene(self, mock_openai_cls, sample_image_b64):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="A quiet residential street with parked cars and trees."
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from tools.vision import execute

        result = await execute(image_base64=sample_image_b64)

        assert result["anomalies"] == [] or len(result["anomalies"]) == 0
