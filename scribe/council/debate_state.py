"""辩论状态数据结构"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WriterOpinion:
    """单个作家的一轮发言"""

    writer_id: str  # e.g. "jiulufeixiang"
    writer_name: str  # e.g. "九鹭非香"
    round: int  # 第几轮
    content: str  # 该轮发言内容
    stance: str  # "support" | "oppose" | "neutral" | "suggest"


@dataclass
class WriterDebateState:
    """辩论全局状态"""

    topic: str  # 讨论主题/用户需求
    user_text: str | None  # 用户提交的文本（审稿场景）
    rounds: int  # 当前轮次
    max_rounds: int  # 最大轮次
    writers: list[str]  # 参与作家ID列表
    history: list[WriterOpinion] = field(default_factory=list)
    per_writer_history: dict[str, list[str]] = field(default_factory=dict)
    current_response: str = ""  # 最新一条发言
    final_proposal: str | None = None  # 主编最终方案
