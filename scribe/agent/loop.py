"""
Agent loop — orchestrates LLM calls, tool execution, and memory integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scribe.types import (
    AuditIssue,
    ChatRequest,
    ChatResponse,
    MemoryEvent,
    Message,
    PersonaConfig,
    Role,
    SessionId,
    ToolCall,
    ToolResult,
    WritingMethodologyConfig,
)

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver
    from scribe.memory.episodic import EpisodicStore
    from scribe.tools.base import ToolContext
    from scribe.tools.registry import ToolRegistry

from scribe.agent.loop_guard import LoopGuard
from scribe.agent.retry import Result, RetryConfig, RetryError, RetryManager
from scribe.agent.token_counter import count_tokens, truncate_messages
from scribe.memory.methodology import WritingMethodology

logger = logging.getLogger(__name__)


# ── Config ──


@dataclass
class AgentConfig:
    max_continuations: int = 5
    tool_timeout_secs: int = 60
    max_tool_result_chars: int = 50_000


# ── Agent Loop ──


class AgentLoop:
    """
    Main agent loop — assembles context, calls LLM, executes tools, manages memory.

    Usage:
        agent = AgentLoop(llm, tools, episodic)
        result = await agent.run(session_id, conversation, model="gpt-4o")
    """

    def __init__(
        self,
        llm: LlmDriver,
        tools: ToolRegistry,
        episodic: EpisodicStore | None = None,
    ):
        self._llm = llm
        self._tools = tools
        self._episodic = episodic
        self._persona: PersonaConfig | None = None
        self._writing_config: WritingMethodologyConfig | None = None
        self._user_name: str = "User"
        self._retry_config = RetryConfig()
        self._agent_config = AgentConfig()

    # ── Builder ──

    def with_persona(self, persona: PersonaConfig) -> AgentLoop:
        self._persona = persona
        return self

    def with_writing_config(self, config: WritingMethodologyConfig) -> AgentLoop:
        self._writing_config = config
        return self

    def with_user_name(self, name: str) -> AgentLoop:
        self._user_name = name
        return self

    def with_retry_config(self, config: RetryConfig) -> AgentLoop:
        self._retry_config = config
        return self

    def with_agent_config(self, config: AgentConfig) -> AgentLoop:
        self._agent_config = config
        return self

    # ── Public Run ──

    async def run(
        self,
        session_id: SessionId,
        conversation: list[Message],
        model: str,
    ) -> str:
        """Blocking run — calls LLM, executes tools, returns final text."""
        return await self._run_impl(session_id, conversation, model, None, None)

    async def run_with_cancel(
        self,
        session_id: SessionId,
        conversation: list[Message],
        model: str,
        cancel_event: asyncio.Event | None = None,
        stream_queue: asyncio.Queue[str] | None = None,
    ) -> str:
        """Run with cancellation support and optional streaming."""
        return await self._run_impl(
            session_id, conversation, model, cancel_event, stream_queue
        )

    # ── Streaming helper ──

    async def chat_with_stream(
        self,
        req: ChatRequest,
        stream_queue: asyncio.Queue[str],
    ) -> ChatResponse:
        """
        Call LLM via stream_chat, accumulate content, forward deltas to stream_queue.
        Falls back to non-streaming if streaming produces no content.
        """
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def _stream_task():
            try:
                await self._llm.stream_chat(req, queue)
            except Exception as e:
                logger.warning("stream_chat failed, falling back to chat(): %s", e)

        task = asyncio.create_task(_stream_task())

        full_content = ""

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=120.0)
                except TimeoutError:
                    break

                if chunk:
                    full_content += chunk
                    await stream_queue.put(chunk)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Fallback if no content
        if not full_content:
            return await self._llm.chat(req)

        return ChatResponse(
            content=full_content if full_content else None,
        )

    # ── Audit ──

    async def run_with_audit(
        self,
        session_id: SessionId,
        conversation: list[Message],
        model: str,
    ) -> str:
        """
        Run with writing audit: generate → audit → re-generate if critical issues.
        """
        wc = self._writing_config
        if not wc or not wc.enabled or not wc.audit_enabled:
            return await self.run(session_id, conversation, model)

        max_retries = 2
        current_conversation = list(conversation)
        last_result = ""

        for attempt in range(max_retries + 1):
            last_result = await self.run(session_id, current_conversation, model)

            # Audit the result
            critical = self._filter_critical_issues(last_result, wc)

            if not critical or attempt == max_retries:
                return last_result

            # Inject audit feedback
            feedback = self._build_audit_feedback(critical)
            current_conversation.extend(
                [
                    Message(role=Role.ASSISTANT, content=last_result),
                    Message(role=Role.USER, content=feedback),
                ]
            )

        return last_result

    # ── Internal ──

    async def _run_impl(
        self,
        session_id: SessionId,
        conversation: list[Message],
        model: str,
        cancel_event: asyncio.Event | None = None,
        stream_queue: asyncio.Queue[str] | None = None,
    ) -> str:
        # 1. Record user event
        await self._record_user_event(session_id, conversation)

        # 2. Assemble system prompt
        system_prompt = await self._assemble_system_prompt()

        # 3. Build message list
        messages: list[Message] = [
            Message(role=Role.SYSTEM, content=system_prompt),
        ]
        messages.extend(conversation)

        # 4. Agent loop
        loop_guard = LoopGuard()
        continuations = 0
        tool_defs = self._tools.definitions()
        max_ctx = self._llm.max_context_tokens()
        system_tokens = count_tokens(system_prompt)
        use_stream = stream_queue is not None

        while True:
            # Cancellation check
            if cancel_event and cancel_event.is_set():
                return "Cancelled."

            # Truncate to fit context
            truncated = truncate_messages(system_tokens, messages[1:], max_ctx)
            full_messages = [messages[0]] + truncated

            req = ChatRequest(
                model=model,
                messages=full_messages,
                tools=tool_defs if tool_defs else None,
                temperature=0.7,
                max_tokens=4096,
                stream=False,
            )

            # Call LLM (streaming or not)
            if use_stream and stream_queue is not None:
                response = await self.chat_with_stream(req, stream_queue)
            else:
                response = await self._llm.chat(req)

            tool_calls = response.tool_calls or []

            if not tool_calls:
                # No tool calls — return the response
                content = response.content or ""
                await self._record_assistant_event(session_id, content)
                return content

            # Append assistant message with tool calls
            messages.append(
                Message(
                    role=Role.ASSISTANT,
                    content=response.content or "",
                    tool_calls=tool_calls,
                )
            )

            # Execute tools
            from scribe.tools.base import ToolContext

            ctx = ToolContext(working_dir=Path.cwd())

            for tc in tool_calls:
                try:
                    loop_guard.check(tc.function.name, tc.function.arguments)
                except ValueError as e:
                    messages.append(
                        Message(
                            role=Role.TOOL,
                            content=str(e),
                            name=tc.function.name,
                            tool_call_id=tc.id,
                        )
                    )
                    continue

                result = await self._execute_tool(tc, ctx)
                content = result.content
                if len(content) > self._agent_config.max_tool_result_chars:
                    content = (
                        content[: self._agent_config.max_tool_result_chars]
                        + "\n\n[truncated]"
                    )

                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=content,
                        name=tc.function.name,
                        tool_call_id=tc.id,
                    )
                )

            continuations += 1
            if continuations >= self._agent_config.max_continuations:
                return (
                    "Reached maximum continuation limit. Please continue your request."
                )

    async def _execute_tool(
        self,
        tc: ToolCall,
        ctx: ToolContext,
    ) -> ToolResult:
        """Execute a single tool call with retry and timeout."""

        tool = self._tools.get(tc.function.name)
        if not tool:
            return ToolResult(
                content=f"Unknown tool: {tc.function.name}",
                is_error=True,
            )

        try:
            params = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            params = {}

        retry_mgr = RetryManager(self._retry_config)
        timeout = self._agent_config.tool_timeout_secs

        async def _call():
            try:
                result = await tool.execute(params, ctx)
                if result.is_error:
                    return Result.err(result.content)
                return Result.ok(result)
            except Exception as e:
                return Result.err(str(e))

        try:
            return await retry_mgr.execute_with_timeout(float(timeout), _call)
        except RetryError as e:
            logger.warning("Tool execution failed after retries: %s", e)
            return ToolResult(content=f"Tool execution failed: {e}", is_error=True)

    async def _record_user_event(
        self, session_id: SessionId, conversation: list[Message]
    ):
        """Record the last user message in episodic memory."""
        if not self._episodic:
            return
        if not conversation or conversation[-1].role != Role.USER:
            return

        msg = conversation[-1]
        event = MemoryEvent(
            id=0,
            session_id=session_id,
            role=Role.USER,
            content=msg.content,
            timestamp=datetime.now(),
            tags=[],
            tool_call_id=None,
            tool_calls=None,
            tool_name=None,
        )
        try:
            await self._episodic.record_event(event)
        except Exception as e:
            logger.warning("Failed to record user event: %s", e)

    async def _record_assistant_event(self, session_id: SessionId, content: str):
        """Record assistant response in episodic memory."""
        if not self._episodic:
            return
        event = MemoryEvent(
            id=0,
            session_id=session_id,
            role=Role.ASSISTANT,
            content=content,
            timestamp=datetime.now(),
            tags=[],
            tool_call_id=None,
            tool_calls=None,
            tool_name=None,
        )
        try:
            await self._episodic.record_event(event)
        except Exception as e:
            logger.warning("Failed to record assistant event: %s", e)

    async def _assemble_system_prompt(self) -> str:
        """Assemble system prompt from persona and writing config."""
        parts: list[str] = []

        # 1. 人格（身份 + 说话风格）
        if self._persona:
            parts.append(self._persona.identity)
            if self._persona.ishiki:
                parts.append(self._persona.ishiki)

        # 2. 写作方法论（全局约束）
        if self._writing_config and self._writing_config.enabled:
            parts.append(WritingMethodology.build_prompt(self._writing_config))

        return "\n\n".join(parts) if parts else "You are a helpful assistant."

    def _filter_critical_issues(
        self, text: str, config: WritingMethodologyConfig
    ) -> list[AuditIssue]:
        """Simple rule-based audit. Returns critical issues found."""
        issues: list[AuditIssue] = []
        lines = text.split("\n")
        char_count = len(text)

        if config.density_rules:
            if config.density_rules.hook_per_chars > 0:
                paragraphs = [line for line in lines if len(line) > 40]
                if paragraphs:
                    avg = char_count / max(len(paragraphs), 1)
                    if avg > config.density_rules.hook_per_chars * 3:
                        issues.append(
                            AuditIssue(
                                category="hook_density",
                                severity="critical",
                                location="overall",
                                suggestion="Add more hooks or shorter paragraphs.",
                            )
                        )

        if config.paragraph_rules:
            short_count = sum(
                1
                for line in lines
                if 0 < len(line) < config.paragraph_rules.min_narrative_chars
            )
            if short_count > config.paragraph_rules.max_short_paragraphs:
                issues.append(
                    AuditIssue(
                        category="short_paragraphs",
                        severity="critical",
                        location=f"{short_count} short paragraphs",
                        suggestion="Consolidate short paragraphs or expand their content.",
                    )
                )

        return issues

    @staticmethod
    def _build_audit_feedback(issues: list[AuditIssue]) -> str:
        """Build user-facing feedback string from audit issues."""
        feedback = "请根据以下审计结果修订文本：\n"
        for issue in issues:
            feedback += (
                f"- [{issue.severity}] {issue.category}: "
                f"{issue.suggestion} ({issue.location})\n"
            )
        return feedback
