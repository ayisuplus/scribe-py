"""Writer Council 向导流程"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.council.router import WriterRouter
from scribe.council.council import CouncilOrchestrator, CouncilConfig

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver
    from scribe.bookshelf import Bookshelf, Book


@dataclass
class ThemeSummary:
    """主题摘要"""

    genre: str
    emotion: str
    protagonist: str
    desire: str
    conflict: str
    setting: str
    effect: str
    scene: str | None

    @classmethod
    def from_answers(cls, answers: dict[str, str]) -> ThemeSummary:
        """从问答答案创建"""
        return cls(
            genre=answers.get("genre", ""),
            emotion=answers.get("emotion", ""),
            protagonist=answers.get("protagonist", ""),
            desire=answers.get("desire", ""),
            conflict=answers.get("conflict", ""),
            setting=answers.get("setting", ""),
            effect=answers.get("effect", ""),
            scene=answers.get("scene"),
        )

    @property
    def summary(self) -> str:
        """生成汇总文本，供WriterRouter使用"""
        parts = [
            f"类型：{self.genre}",
            f"情绪：{self.emotion}",
            f"主角：{self.protagonist}",
            f"目标：{self.desire}",
            f"冲突：{self.conflict}",
            f"世界观：{self.setting}",
            f"效果：{self.effect}",
        ]
        if self.scene:
            parts.append(f"场景：{self.scene}")
        return "\n".join(parts)


@dataclass
class WritingScope:
    """写作范围"""

    mode: str           # "outline" | "chapter" | "volume" | "full"
    target: str | None  # e.g. "第3章", "卷二", None
    description: str    # 人类可读描述
