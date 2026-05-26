"""
LLM driver module.
"""

from scribe.llm.base import LlmDriver
from scribe.llm.openai import OpenAiDriver
from scribe.llm.deepseek import DeepSeekDriver
from scribe.llm.anthropic import AnthropicDriver


def create_llm(provider: str, model: str) -> LlmDriver:
    """Create an LLM driver for a configured provider/model pair."""
    if provider == "anthropic":
        return AnthropicDriver(model=model)
    if provider == "deepseek":
        return DeepSeekDriver(model=model)
    return OpenAiDriver(model=model)


__all__ = [
    "LlmDriver",
    "OpenAiDriver",
    "DeepSeekDriver",
    "AnthropicDriver",
    "create_llm",
]
