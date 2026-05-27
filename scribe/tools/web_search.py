"""
Web search tool using DuckDuckGo Lite.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import quote

import httpx

from scribe.tools.base import Tool
from scribe.types import ToolResult

if TYPE_CHECKING:
    from scribe.tools.base import ToolContext


# Simple HTTP-based search (no API key required)
SEARCH_URL = "https://lite.duckduckgo.com/lite/?q={q}"

# Regex patterns for parsing DDG Lite results
_LINK_RE = re.compile(
    r'<a\s+[^>]*href="([^"]+)"[^>]*class="[^"]*result-link[^"]*"[^>]*>([^<]+)</a>'
)
_GENERIC_LINK_RE = re.compile(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>([^<]+)</a>')
_SNIPPET_RE = re.compile(
    r'<span\s+class=["\']?(?:snippet|result-snippet)["\']?[^>]*>([^<]*)</span>'
)


def _parse_ddg_lite(html: str) -> list[str]:
    """Parse DuckDuckGo Lite HTML for search results."""
    results: list[str] = []

    # Try structured result links first
    for cap in _LINK_RE.finditer(html):
        url = cap[1].strip()
        title = cap[2].strip()
        if not title or "duckduckgo.com" in url:
            continue
        results.append(f"{title}\n  {url}")

    # Fallback: generic link parsing
    if not results:
        for cap in _GENERIC_LINK_RE.finditer(html):
            href = cap[1].strip()
            title = cap[2].strip()
            if (
                not title
                or "duckduckgo.com" in href
                or href.startswith("//")
                or title == "More results"
            ):
                continue
            results.append(f"{title}\n  {href}")

    # Enrich with snippets
    snippets = [m[1].strip() for m in _SNIPPET_RE.finditer(html)]
    for i, snippet in enumerate(snippets):
        if i < len(results) and snippet:
            results[i] = f"{results[i]}\n  {snippet}"

    return results[:5]


class WebSearchTool(Tool):
    """
    Search the web for information.
    Returns relevant results with title, snippet, and URL.
    """

    def name(self) -> str:
        return "web_search"

    def description(self) -> str:
        return "Search the web for information. Returns relevant results with title, snippet, and URL."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        query = params.get("query")
        if not query:
            return ToolResult(content="Missing 'query' parameter", is_error=True)

        encoded = quote(query)
        url = SEARCH_URL.format(q=encoded)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={"User-Agent": "Scribe/0.1"})
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            return ToolResult(content=f"Search failed: {e}", is_error=True)

        results = _parse_ddg_lite(html)

        if not results:
            return ToolResult(content=f"No results found for: {query}", is_error=False)

        content = "\n---\n".join(results)
        return ToolResult(content=content, is_error=False)
