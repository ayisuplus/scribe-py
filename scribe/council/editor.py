"""主编裁决 — 综合辩论内容产出最终方案"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from scribe.agent.loop import AgentLoop
from scribe.council.debate_state import WriterDebateState
from scribe.tools.registry import ToolRegistry
from scribe.types import Message, PersonaConfig, Role, SessionId

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver

logger = logging.getLogger(__name__)


DEFAULT_EDITOR_IDENTITY = """你是一位资深写作主编。你的任务是综合多位作家的讨论意见，产出一个完整的、可执行的写作方案。

你的输出必须包含：
1. **共识要点**：所有作家一致认同的观点
2. **分歧分析**：存在争议的点，以及你的判断
3. **最终方案**：可直接执行的写作建议或修改方案

请用结构化格式输出。"""


class EditorAgent:
    """裁决型主编 — 综合所有辩论内容，产出最终方案"""

    def __init__(
        self,
        llm: LlmDriver,
        editor_persona: PersonaConfig | None = None,
    ):
        if editor_persona is None:
            editor_persona = PersonaConfig(
                identity=DEFAULT_EDITOR_IDENTITY,
                ishiki="",
            )
        self._agent = AgentLoop(llm, ToolRegistry()).with_persona(editor_persona)

    async def synthesize(
        self,
        state: WriterDebateState,
        session_id: SessionId,
        model: str,
    ) -> str:
        """综合辩论记录，输出最终裁决方案"""
        prompt = self._build_synthesis_prompt(state)
        conversation = [Message(role=Role.USER, content=prompt)]
        return await self._agent.run(session_id, conversation, model)

    def _build_synthesis_prompt(self, state: WriterDebateState) -> str:
        """构建裁决prompt"""
        parts = []

        parts.append("# 作家团讨论记录\n")

        # 用户需求
        parts.append(f"## 用户需求\n{state.topic}")

        # 用户文本
        if state.user_text:
            parts.append(f"\n## 用户提交的文本\n{state.user_text}")
        else:
            parts.append("\n## 用户提交的文本\n（无，本次是创作构思场景）")

        # 辩论记录
        parts.append("\n## 辩论记录")
        for op in state.history:
            parts.append(
                f"\n### 【{op.writer_name}·第{op.round}轮·{op.stance}】\n{op.content}"
            )

        # 裁决指令
        parts.append("""
## 你的任务

请综合以上所有作家的讨论，产出最终方案：

1. **共识要点**：哪些观点得到了多位作家的认同？
2. **分歧分析**：存在哪些争议？你倾向于哪一方？为什么？
3. **最终方案**：一个完整的、可直接执行的写作建议或修改方案

请用清晰的结构化格式输出。""")

        return "\n".join(parts)
