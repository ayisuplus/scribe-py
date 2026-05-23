"""
Retry mechanism with exponential backoff.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Callable, TypeVar

from dataclasses import dataclass


T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt with jitter (±10%)."""
        base = self.initial_delay_ms * (self.backoff_multiplier ** attempt)
        capped = min(base, self.max_delay_ms)
        jitter = capped * 0.1 * (1.0 - random.random() * 2.0)
        return (capped + jitter) / 1000.0  # seconds


class RetryableError:
    """Error categorization."""
    TRANSIENT = "transient"
    BUSINESS_LOGIC = "business_logic"
    UNKNOWN = "unknown"


def _classify_error(message: str) -> str:
    """Classify an error message as retryable or not."""
    msg = message.lower()

    # Transient errors
    transient_keywords = [
        "timeout", "timed out", "deadline exceeded",
        "connection", "network", "dns", "refused", "reset",
        "broken pipe", "econnrefused", "econnreset", "enetunreach",
        "etimedout", "too many requests", "rate limit",
        "429", "503", "502", "unavailable",
    ]
    for kw in transient_keywords:
        if kw in msg:
            return RetryableError.TRANSIENT

    # Business logic errors
    business_keywords = [
        "unknown tool", "invalid parameters",
        "permission denied", "unauthorized", "forbidden",
    ]
    for kw in business_keywords:
        if kw in msg:
            return RetryableError.BUSINESS_LOGIC

    return RetryableError.UNKNOWN


class RetryError(Exception):
    """Errors during retry operations."""
    def __init__(self, message: str, error_type: str):
        super().__init__(message)
        self.error_type = error_type


class RetryManager:
    """
    Execute async operations with exponential backoff retry.
    """

    def __init__(self, config: RetryConfig | None = None):
        self._config = config or RetryConfig()

    async def execute(
        self,
        operation: Callable[[], "asyncio.Future[Result[T]]"],
    ) -> T:
        """
        Execute an async operation with retry logic.
        operation: callable returning an asyncio.Future[Result[T]].
        Result[T] is a Result[T, str] (Ok value or Err string).
        """
        last_error: str | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                result = await operation()
                if result.is_ok():
                    return result.ok_value
                error_msg = result.error_value
                error_class = _classify_error(error_msg)

                if error_class == RetryableError.BUSINESS_LOGIC:
                    raise RetryError(error_msg, RetryableError.BUSINESS_LOGIC)

                last_error = error_msg
            except RetryError as e:
                if e.error_type == RetryableError.BUSINESS_LOGIC:
                    raise
                last_error = str(e)

            if attempt < self._config.max_retries:
                delay = self._config.calculate_delay(attempt)
                await asyncio.sleep(delay)

        raise RetryError(
            last_error or "Unknown error",
            RetryableError.TRANSIENT,
        )

    async def execute_with_timeout(
        self,
        timeout: float,
        operation: Callable[[], "asyncio.Future[Result[T]]"],
    ) -> T:
        """
        Execute with timeout. Timeout counts as a transient error.
        """
        last_error: str | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    operation(),
                    timeout=timeout,
                )
                if result.is_ok():
                    return result.ok_value
                error_msg = result.error_value
                error_class = _classify_error(error_msg)

                if error_class == RetryableError.BUSINESS_LOGIC:
                    raise RetryError(error_msg, RetryableError.BUSINESS_LOGIC)

                last_error = error_msg
            except asyncio.TimeoutError:
                last_error = f"Operation timed out after {timeout}s"
            except RetryError as e:
                if e.error_type == RetryableError.BUSINESS_LOGIC:
                    raise
                last_error = str(e)

            if attempt < self._config.max_retries:
                delay = self._config.calculate_delay(attempt)
                await asyncio.sleep(delay)

        raise RetryError(
            last_error or "Unknown error",
            RetryableError.TRANSIENT,
        )


# Simple Result type (not stdlib)
class Result:
    __slots__ = ("_ok", "_err", "_ok_val", "_err_val")

    def __init__(self, ok_val=None, err_val=None):
        self._ok = err_val is None
        self._err = err_val is not None
        self._ok_val = ok_val
        self._err_val = err_val

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(ok_val=value)

    @classmethod
    def err(cls, value: str) -> "Result[T]":
        return cls(err_val=value)

    @property
    def ok_value(self) -> T:
        return self._ok_val

    @property
    def error_value(self) -> str:
        return self._err_val

    def is_ok(self) -> bool:
        return self._ok

    def is_err(self) -> bool:
        return self._err