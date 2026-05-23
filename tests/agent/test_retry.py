"""
Tests for RetryManager exponential backoff.
"""

import asyncio
import pytest

from scribe.agent.retry import (
    RetryConfig,
    RetryManager,
    RetryError,
    Result,
    _classify_error,
)


class TestClassifyError:
    def test_transient_timeout(self):
        assert _classify_error("timeout error") == "transient"
        assert _classify_error("Request timed out after 60s") == "transient"

    def test_transient_connection(self):
        assert _classify_error("Connection refused") == "transient"
        assert _classify_error("Network error") == "transient"
        assert _classify_error("ETIMEDOUT") == "transient"

    def test_transient_rate_limit(self):
        assert _classify_error("429 Too Many Requests") == "transient"
        assert _classify_error("rate limit exceeded") == "transient"

    def test_business_logic(self):
        assert _classify_error("Unknown tool: foo") == "business_logic"
        assert _classify_error("Invalid parameters") == "business_logic"


class TestRetryConfig:
    def test_default_values(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.initial_delay_ms == 1000
        assert cfg.max_delay_ms == 30000
        assert cfg.backoff_multiplier == 2.0

    def test_exponential_backoff(self):
        cfg = RetryConfig(initial_delay_ms=1000, backoff_multiplier=2.0, max_delay_ms=100000)
        # Attempt 0: 1000 * 2^0 = 1000ms
        # Attempt 1: 1000 * 2^1 = 2000ms
        # Attempt 2: 1000 * 2^2 = 4000ms
        delays = [cfg.calculate_delay(i) for i in range(3)]
        assert 0.9 <= delays[0] <= 1.1  # ~1s
        assert 1.8 <= delays[1] <= 2.2  # ~2s
        assert 3.6 <= delays[2] <= 4.4  # ~4s

    def test_max_delay_cap(self):
        cfg = RetryConfig(initial_delay_ms=1000, max_delay_ms=500, backoff_multiplier=10.0)
        d = cfg.calculate_delay(3)  # Would be 1000 * 10^3 = 10s, but capped at 500ms
        assert d <= 0.55  # 500ms + 10% jitter


class TestRetryManager:
    @pytest.mark.asyncio
    async def test_success_first_try(self):
        cfg = RetryConfig(max_retries=3, initial_delay_ms=10)
        mgr = RetryManager(cfg)

        result = await mgr.execute(lambda: asyncio.sleep(0, Result.ok(42)))
        assert result == 42

    @pytest.mark.asyncio
    async def test_retries_on_transient(self):
        cfg = RetryConfig(max_retries=2, initial_delay_ms=10)
        mgr = RetryManager(cfg)
        attempts = [0]

        async def flaky():
            attempts[0] += 1
            if attempts[0] < 3:
                return Result.err("Connection refused")
            return Result.ok(42)

        result = await mgr.execute(flaky)
        assert result == 42
        assert attempts[0] == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_business_error(self):
        cfg = RetryConfig(max_retries=5, initial_delay_ms=10)
        mgr = RetryManager(cfg)

        async def biz_error():
            return Result.err("Unknown tool: foo")

        with pytest.raises(RetryError) as exc_info:
            await mgr.execute(biz_error)
        assert exc_info.value.error_type == "business_logic"

    @pytest.mark.asyncio
    async def test_exhausted_after_max_retries(self):
        cfg = RetryConfig(max_retries=2, initial_delay_ms=10)
        mgr = RetryManager(cfg)

        async def always_fail():
            return Result.err("Connection refused")

        with pytest.raises(RetryError) as exc_info:
            await mgr.execute(always_fail)
        assert "Connection refused" in str(exc_info.value)


class TestRetryManagerTimeout:
    @pytest.mark.asyncio
    async def test_timeout_counts_as_transient(self):
        cfg = RetryConfig(max_retries=1, initial_delay_ms=10)
        mgr = RetryManager(cfg)

        async def slow():
            await asyncio.sleep(10)  # much longer than timeout
            return Result.ok(42)

        with pytest.raises(RetryError) as exc_info:
            await mgr.execute_with_timeout(0.1, slow)
        assert "timed out" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])