"""Web search tool — searches the internet and summarizes results."""

import logging

import httpx
from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

# Free search APIs (no key needed)
SEARCH_ENDPOINTS = [
    "https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1",
]


async def execute(query: str, max_results: int = 5) -> dict:
    """Search the web for information and return a summarized result.

    Params:
        query: Search query string
        max_results: Maximum number of results to summarize

    Returns: {results: list, summary: str, sources: list, error: str|None}
    """
    try:
        results = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Try DuckDuckGo Instant Answer API
            url = SEARCH_ENDPOINTS[0].format(query=query)
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Abstract (instant answer)
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", ""),
                        "snippet": data["Abstract"],
                        "url": data.get("AbstractURL", ""),
                        "source": data.get("AbstractSource", ""),
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:80],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                            "source": "DuckDuckGo",
                        })

        if not results:
            return {
                "results": [],
                "summary": f"No web results found for: {query}",
                "sources": [],
                "error": None,
            }

        # Summarize results with LLM
        context = "\n\n".join(
            f"[{i+1}] {r['title']}: {r['snippet'][:300]}" for i, r in enumerate(results[:max_results])
        )

        try:
            llm_client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")
            response = await llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Summarize the following search results concisely. Cite sources as [1], [2], etc."},
                    {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}"},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            summary = response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            summary = results[0]["snippet"] if results else "No summary available."

        sources = [{"title": r["title"], "url": r["url"]} for r in results if r.get("url")]

        return {
            "results": results[:max_results],
            "summary": summary,
            "sources": sources,
            "error": None,
        }

    except Exception as e:
        logger.exception("Web search failed")
        return {
            "results": [],
            "summary": "",
            "sources": [],
            "error": str(e),
        }
