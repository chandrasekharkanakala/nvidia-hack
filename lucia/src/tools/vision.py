"""Vision tool — analyze images via NeVA-7B vision model."""

import base64
import logging

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


async def execute(image_base64: str, question: str = "Describe this image") -> dict:
    """Analyze an image using NeVA-7B vision model."""
    try:
        client = AsyncOpenAI(
            base_url="http://localhost:8003/v1",
            api_key="not-needed",
        )

        # Ensure proper base64 data URL format
        if not image_base64.startswith("data:"):
            image_url = f"data:image/jpeg;base64,{image_base64}"
        else:
            image_url = image_base64

        response = await client.chat.completions.create(
            model="neva-7b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=1024,
            temperature=0.2,
        )

        description = response.choices[0].message.content

        # Parse structured info from description
        objects_detected = []
        anomalies = []

        lines = description.lower().split(".")
        for line in lines:
            line = line.strip()
            if any(kw in line for kw in ["vehicle", "car", "bus", "truck", "bicycle", "pedestrian", "person"]):
                objects_detected.append(line)
            if any(kw in line for kw in ["accident", "collision", "damage", "blocked", "flood", "fire", "unusual"]):
                anomalies.append(line)

        return {
            "description": description,
            "objects_detected": objects_detected,
            "anomalies": anomalies,
            "error": None,
        }

    except Exception as e:
        logger.exception("Vision tool failed")
        return {
            "description": "",
            "objects_detected": [],
            "anomalies": [],
            "error": str(e),
        }
