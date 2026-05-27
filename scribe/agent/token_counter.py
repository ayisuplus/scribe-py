"""
Token counting and conversation truncation.
"""

from scribe.types import Message


def count_tokens(text: str) -> int:
    """
    Approximate token count for mixed Chinese/English text.
    English: ~4 chars/token, CJK: ~1.6 chars/token.
    """
    chars = list(text)
    tokens = 0.0
    for c in chars:
        if c.isascii():
            tokens += 0.25
        else:
            tokens += 0.6
    return int(tokens)


def count_message_tokens(messages: list[Message]) -> int:
    """Total tokens across messages (~4 tokens/message overhead for role formatting)."""
    return sum(count_tokens(m.content) + 4 for m in messages)


def truncate_messages(
    system_prompt_len: int,
    messages: list[Message],
    max_tokens: int,
) -> list[Message]:
    """
    Truncate conversation messages to fit within max_tokens,
    keeping the system prompt intact and removing oldest non-system messages first.
    """
    available = max_tokens - system_prompt_len - 512  # reserve for response
    if available <= 0:
        return []

    kept: list[Message] = []
    used = 0

    # Keep newest messages first
    for msg in reversed(messages):
        t = count_tokens(msg.content) + 4
        if used + t <= available:
            used += t
            kept.append(msg)
        else:
            break

    kept.reverse()
    return kept
