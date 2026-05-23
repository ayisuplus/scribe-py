"""
Loop guard — detects repeated tool calls with identical arguments.
"""

from __future__ import annotations

import hashlib


class LoopGuard:
    """
    Tracks tool calls by hashing (tool_name + arguments).
    Warns on warn_threshold hits, blocks on block_threshold hits.
    """

    def __init__(
        self,
        warn_threshold: int = 3,
        block_threshold: int = 5,
    ):
        self._seen_hashes: dict[str, int] = {}
        self._warn_threshold = warn_threshold
        self._block_threshold = block_threshold

    def check(self, tool_name: str, arguments: str) -> None:
        """
        Check a tool call.
        Returns None if OK, raises ValueError if loop detected.
        """
        hasher = hashlib.sha256()
        hasher.update(f"{tool_name}:{arguments}".encode())
        hash_val = hasher.hexdigest()

        count = self._seen_hashes.get(hash_val, 0) + 1
        self._seen_hashes[hash_val] = count

        if count >= self._block_threshold:
            raise ValueError(
                f"Loop detected: tool '{tool_name}' called {count} times with same arguments. Blocking."
            )

    def reset(self) -> None:
        """Clear all tracked call hashes."""
        self._seen_hashes.clear()