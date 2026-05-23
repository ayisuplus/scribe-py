"""作家代理 — 将 AgentLoop + PersonaConfig + 辩论prompt 组合"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.types import Message, Role, SessionId
from scribe.agent.loop import AgentLoop
from scribe.tools.registry import ToolRegistry
from scribe.council.debate_state import WriterDebateState, WriterOpinion

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver
    from scribe.types import PersonaConfig

logger = logging.getLogger(__name__)


class WriterAgent:
    """单个作家代理 — 加载人格，参与辩论"""

    def __init__(
        self,
        writer_id: str,
        llm: LlmDriver,
        persona: PersonaConfig,
    ):
        self.writer_id = writer_id
        self._persona = persona
        self._agent = AgentLoop(llm, ToolRegistry()).with_persona(persona)

    @property
    def _writer_name(self) -> str:
        """Extract writer name from persona config, falling back to writer_id."""
        return self._persona.name or self.writer_id

    async def debate(
        self,
        state: WriterDebateState,
        session_id: SessionId,
        model: str,
    ) -> WriterOpinion:
        """根据当前辩论状态，产出该作家的下一轮发言"""
        prompt = self._build_debate_prompt(state)
        conversation = [Message(role=Role.USER, content=prompt)]
        content = await self._agent.run(session_id, conversation, model)

        return WriterOpinion(
            writer_id=self.writer_id,
            writer_name=self._writer_name,
            round=state.rounds,
            content=content,
            stance=self._extract_stance(content),
        )

    def _build_debate_prompt(self, state: WriterDebateState) -> str:
        """构建辩论prompt"""
        parts = []

        # 角色说明
        parts.append(f"你现在以「{self._writer_name}」的身份参与一场写作讨论。")

        # 用户需求
        parts.append(f"\n## 讨论主题\n{state.topic}")

        # 用户提交的文本
        if state.user_text:
            parts.append(f"\n## 用户提交的文本\n{state.user_text}")

        # 自己的历史发言
        my_history = state.per_writer_history.get(self.writer_id, [])
        if my_history:
            history_text = "\n".join(f"- 第{i+1}轮: {h}" for i, h in enumerate(my_history))
            parts.append(f"\n## 你之前的发言\n{history_text}")

        # 其他作家的最新发言
        other_opinions = [
            op for op in state.history
            if op.writer_id != self.writer_id and op.round == state.rounds - 1
        ]
        if other_opinions:
            others_text = "\n".join(
                f"- 【{op.writer_name}】: {op.content}" for op in other_opinions
            )
            parts.append(f"\n## 其他作家的上一轮发言\n{others_text}")

        # 当前轮次指令
        parts.append(f"\n## 当前：第{state.rounds}轮（共{state.max_rounds}轮）")
        parts.append("\n请从你的专业视角出发，对讨论主题发表看法。可以赞同、反对或补充其他作家的观点。保持你的个人风格。")

        return "\n".join(parts)

    def _extract_stance(self, content: str) -> str:
        """从发言内容中提取立场标签"""
        content_lower = content
        if any(w in content_lower for w in ["同意", "赞同", "说得对", "很好", "认可"]):
            return "support"
        if any(w in content_lower for w in ["反对", "不行", "不同意", "不认可", "问题"]):
            return "oppose"
        if any(w in content_lower for w in ["建议", "试试", "可以考虑", "不妨", "推荐"]):
            return "suggest"
        return "neutral"
