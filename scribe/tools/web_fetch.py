"""
Web fetch tool.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import httpx

from scribe.tools.base import Tool
from scribe.types import ToolResult

if TYPE_CHECKING:
    from scribe.tools.base import ToolContext


_PRIVATE_HOSTS = frozenset(
    [
        "localhost",
        "127.0.0.1",
        "::1",
        "169.254.169.254",
    ]
)
_PRIVATE_PREFIXES = (
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
)


def _is_private_host(host: str) -> bool:
    """Check if a hostname resolves to a private/internal IP."""
    if host in _PRIVATE_HOSTS:
        return True
    if host.startswith(_PRIVATE_PREFIXES):
        return True
    if "metadata.google" in host or "169.254.169.254" in host:
        return True
    return False


# Regex patterns for HTML text extraction
_SCRIPT_RE = re.compile(r"(?is)<script[^>]*>.*?</script>", re.DOTALL)
_STYLE_RE = re.compile(r"(?is)<style[^>]*>.*?</style>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_NL_RE = re.compile(r"\n\s*\n\s*\n+")
_WS_RE = re.compile(r"[ \t]+")
_NL_WS_RE = re.compile(r"\n[ \t]+")
_WS_NL_RE = re.compile(r"[ \t]+\n")


def _extract_text_from_html(html: str) -> str:
    """Strip tags, scripts, styles; collapse whitespace."""
    text = _SCRIPT_RE.sub("", html)
    text = _STYLE_RE.sub("", text)
    text = _TAG_RE.sub(" ", text)

    # Decode common HTML entities
    for src, dst in [
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
        ("&nbsp;", " "),
    ]:
        text = text.replace(src, dst)

    # Collapse whitespace
    text = _MULTI_NL_RE.sub("\n\n", text)
    text = _WS_RE.sub(" ", text)
    text = _NL_WS_RE.sub("\n", text)
    text = _WS_NL_RE.sub("\n", text)

    # Trim each line
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


MAX_CONTENT_CHARS = 50_000


class WebFetchTool(Tool):
    """
    Fetch and read the content of a web page.
    Extracts readable text from HTML. Blocks private/internal addresses.
    """

    def name(self) -> str:
        return "web_fetch"

    def description(self) -> str:
        return "Fetch and read the content of a web page. Extracts readable text from HTML."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        url = params.get("url")
        if not url:
            return ToolResult(content="Missing 'url' parameter", is_error=True)

        # Parse and check host
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host = parsed.netloc
            if _is_private_host(host):
                return ToolResult(
                    content="Access to private/local addresses is blocked.",
                    is_error=True,
                )
        except Exception:
            return ToolResult(content=f"Invalid URL: {url}", is_error=True)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers={"User-Agent": "Scribe/0.1"})
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").lower()
                raw = resp.text
        except Exception as e:
            return ToolResult(content=f"Fetch failed: {e}", is_error=True)

        if "html" in content_type:
            extracted = _extract_text_from_html(raw)
        else:
            extracted = raw

        if len(extracted) > MAX_CONTENT_CHARS:
            extracted = f"{extracted[:MAX_CONTENT_CHARS]}\n\n[truncated at {MAX_CONTENT_CHARS} characters]"

        return ToolResult(content=extracted, is_error=False)
