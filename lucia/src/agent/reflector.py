"""LUCIA Agent — Response validation (Deep mode only)."""

import json
import logging

from openai import AsyncOpenAI

from config.settings import settings
from agent.prompts import REFLECTOR_SYSTEM

logger = logging.getLogger(__name__)


async def validate(query: str, tool_results: list[dict]) -> dict:
    """Validate whether tool results adequately answer the query.

    Returns: {confidence: float, grounded: bool, issues: list[str], retry: bool}
    """
    try:
        client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")

        # Summarize tool results for the reflector
        results_summary = []
        for i, r in enumerate(tool_results):
            if r["success"]:
                data_preview = str(r["data"])[:500]
                results_summary.append(f"[{i+1}] {r['tool']}: {data_preview}")
            else:
                results_summary.append(f"[{i+1}] {r['tool']}: FAILED — {r.get('error', 'unknown')}")

        user_content = (
            f"Query: {query}\n\n"
            f"Tool Results:\n" + "\n".join(results_summary)
        )

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": REFLECTOR_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
        result = json.loads(raw)

        confidence = float(result.get("confidence", 0.5))
        grounded = bool(result.get("grounded", True))
        issues = result.get("issues", [])
        retry = confidence < 0.5 or bool(result.get("retry", False))

        return {
            "confidence": confidence,
            "grounded": grounded,
            "issues": issues if isinstance(issues, list) else [],
            "retry": retry,
        }

    except Exception as e:
        logger.warning(f"Reflector validation failed: {e}")
        return {
            "confidence": 0.5,
            "grounded": True,
            "issues": ["Reflection unavailable"],
            "retry": False,
        }
