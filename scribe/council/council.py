"""主编排器 — 管理整个辩论流程"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.types import new_session_id, PersonaConfig
from scribe.council.debate_state import WriterDebateState
from scribe.council.writer_agent import WriterAgent
from scribe.council.editor import EditorAgent

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver

logger = logging.getLogger(__name__)


@dataclass
class CouncilConfig:
    """作家团配置"""

    max_rounds: int = 2
    model: str = "gpt-4o"
    editor_persona: PersonaConfig | None = None
    writer_dir: Path = field(default_factory=lambda: Path("writers/"))


class CouncilOrchestrator:
    """主编排器 — 管理整个辩论流程"""

    def __init__(self, llm: LlmDriver, config: CouncilConfig):
        self._llm = llm
        self._config = config
        self._writers: dict[str, WriterAgent] = {}
        self._editor = EditorAgent(llm, config.editor_persona)

    def register_writer(self, writer_id: str, persona_path: Path) -> None:
        """注册一位作家"""
        from scribe.memory.persona import PersonaLoader
        persona = PersonaLoader.load(persona_path)
        self._writers[writer_id] = WriterAgent(writer_id, self._llm, persona)

    async def run(
        self,
        topic: str,
        writer_ids: list[str],
        user_text: str | None = None,
        max_rounds: int | None = None,
    ) -> str:
        """执行完整辩论流程，返回主编最终方案"""
        session_id = new_session_id()
        rounds = max_rounds or self._config.max_rounds
        model = self._config.model

        state = WriterDebateState(
            topic=topic,
            user_text=user_text,
            rounds=0,
            max_rounds=rounds,
            writers=writer_ids,
            history=[],
            per_writer_history={wid: [] for wid in writer_ids},
            current_response="",
            final_proposal=None,
        )

        # 辩论循环
        for round_num in range(rounds):
            state.rounds = round_num + 1
            for wid in writer_ids:
                writer = self._writers[wid]
                opinion = await writer.debate(state, session_id, model)
                state.history.append(opinion)
                state.per_writer_history[wid].append(opinion.content)
                state.current_response = opinion.content
                logger.info(
                    "Round %d - %s: %s",
                    state.rounds,
                    opinion.writer_name,
                    opinion.content[:50],
                )

        # 主编裁决
        state.final_proposal = await self._editor.synthesize(state, session_id, model)
        return state.final_proposal
