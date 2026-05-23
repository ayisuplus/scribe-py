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


class ScopeParser:
    """解析用户的自由输入为写作范围"""

    def parse(self, user_input: str) -> WritingScope:
        """解析用户输入"""
        text = user_input.strip()

        # 大纲
        if any(k in text for k in ["大纲", "outline", "提纲"]):
            return WritingScope(mode="outline", target=None, description="生成大纲")

        # 整本
        if any(k in text for k in ["整本", "全书", "全部", "整书"]):
            return WritingScope(mode="full", target=None, description="生成整本书")

        # 范围匹配："从第3章到第7章"（必须在章节匹配之前）
        range_match = re.search(r'从.+到', text)
        if range_match:
            return WritingScope(mode="chapter", target=text, description=f"生成{text}")

        # 章节匹配："第3章", "第三章"
        chapter_match = re.search(r'第(\d+|[一二三四五六七八九十百]+)章', text)
        if chapter_match:
            target = chapter_match.group(0)
            return WritingScope(mode="chapter", target=target, description=f"生成{target}")

        # 卷匹配："卷二", "第二卷"
        volume_match = re.search(r'(第?(\d+|[一二三四五六七八九十百]+)卷|卷[一二三四五六七八九十百\d]+)', text)
        if volume_match:
            target = volume_match.group(0)
            return WritingScope(mode="volume", target=target, description=f"生成{target}")

        # 默认：大纲
        return WritingScope(mode="outline", target=None, description="生成大纲")
