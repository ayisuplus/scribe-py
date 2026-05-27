"""Writer Council 向导流程"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.council.council import CouncilConfig, CouncilOrchestrator
from scribe.council.router import WriterRouter

if TYPE_CHECKING:
    from scribe.bookshelf import Book, Bookshelf
    from scribe.llm.base import LlmDriver


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

    def confirm(self, interviewer: ThemeInterviewer) -> ThemeSummary:
        """显示摘要，用户确认。不确认则重新问答。"""
        while True:
            print(f"""
📝 主题摘要：
  类型：{self.genre}
  情绪：{self.emotion}
  主角：{self.protagonist}
  目标：{self.desire}
  冲突：{self.conflict}
  世界观：{self.setting}
  效果：{self.effect}
  场景：{self.scene or "无"}
""")
            if input("确认？(Y/n) ").strip().lower() != "n":
                return self
            new_theme = asyncio.run(interviewer.interview())
            self.genre = new_theme.genre
            self.emotion = new_theme.emotion
            self.protagonist = new_theme.protagonist
            self.desire = new_theme.desire
            self.conflict = new_theme.conflict
            self.setting = new_theme.setting
            self.effect = new_theme.effect
            self.scene = new_theme.scene

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

    mode: str  # "outline" | "chapter" | "volume" | "full"
    target: str | None  # e.g. "第3章", "卷二", None
    description: str  # 人类可读描述


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
        range_match = re.search(r"从.+到", text)
        if range_match:
            return WritingScope(mode="chapter", target=text, description=f"生成{text}")

        # 章节匹配："第3章", "第三章"
        chapter_match = re.search(r"第(\d+|[一二三四五六七八九十百]+)章", text)
        if chapter_match:
            target = chapter_match.group(0)
            return WritingScope(
                mode="chapter", target=target, description=f"生成{target}"
            )

        # 卷匹配："卷二", "第二卷"
        volume_match = re.search(
            r"(第?(\d+|[一二三四五六七八九十百]+)卷|卷[一二三四五六七八九十百\d]+)",
            text,
        )
        if volume_match:
            target = volume_match.group(0)
            return WritingScope(
                mode="volume", target=target, description=f"生成{target}"
            )

        # 默认：大纲
        return WritingScope(mode="outline", target=None, description="生成大纲")


class ThemeInterviewer:
    """通过多轮问答确定写作主题"""

    QUESTIONS = [
        (
            "genre",
            "你想写什么类型？",
            ["仙侠", "都市", "科幻", "纯文学", "历史", "悬疑", "奇幻", "其他"],
        ),
        (
            "emotion",
            "故事的核心情绪是什么？",
            ["热血", "虐心", "温暖", "悬疑", "搞笑", "沉重", "治愈"],
        ),
        ("protagonist", "主角是什么样的人？（身份/性格/缺陷）", None),
        ("desire", "主角最想要什么？（目标/执念）", None),
        (
            "conflict",
            "最大的冲突是什么？",
            ["人与人", "人与命运", "人与自我", "人与社会", "人与自然"],
        ),
        ("setting", "故事发生在哪里？（世界观/时代/地点）", None),
        (
            "effect",
            "你想达到什么效果？",
            ["让读者笑", "让读者哭", "让读者思考", "让读者紧张", "让读者感动"],
        ),
        ("scene", "有什么特别想写的场景或画面吗？（没有可跳过）", None),
    ]

    async def interview(self) -> ThemeSummary:
        """执行问答，返回主题摘要"""
        answers: dict[str, str] = {}
        for key, question, options in self.QUESTIONS:
            if options:
                answer = self._ask_choice(question, options)
            else:
                answer = self._ask_text(question)
            if answer:
                answers[key] = answer
        return ThemeSummary.from_answers(answers)

    def _ask_choice(self, question: str, options: list[str]) -> str:
        """选择题交互"""
        print(f"\n🎯 {question}")
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        while True:
            choice = input("  选择编号: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            except ValueError:
                pass
            print("  无效选择，请重试")

    def _ask_text(self, question: str) -> str:
        """自由输入交互"""
        print(f"\n🎯 {question}")
        return input("  > ").strip()


class CouncilWizard:
    """向导流程 — 选书后自动运行"""

    def __init__(self, llm: LlmDriver, bookshelf: Bookshelf):
        self._llm = llm
        self._bookshelf = bookshelf
        self._router = WriterRouter()
        self._interviewer = ThemeInterviewer()
        self._scope_parser = ScopeParser()

    async def run(self, book: Book) -> str:
        """完整向导流程，返回主编最终方案"""
        # Step 1: 主题问答
        theme = await self._interviewer.interview()
        theme.confirm(self._interviewer)

        # Step 2: 选作家
        recommended = self._router.recommend(theme.summary)
        writer_ids = self._select_writers(recommended)

        # Step 3: 输入范围
        scope_text = input("\n📐 你想写什么？（大纲/第X章/整本）: ").strip()
        scope = self._scope_parser.parse(scope_text)
        print(f"  范围：{scope.description}")

        # Step 4: 初始化Council
        config = CouncilConfig(max_rounds=2)
        council = CouncilOrchestrator(self._llm, config)

        for wid in writer_ids:
            persona_path = Path(f"writers/{wid}-perspective")
            council.register_writer(wid, persona_path)

        # Step 5: 构建主题prompt
        topic = self._build_topic(theme, scope, book)

        # Step 6: 执行辩论+写作
        print("\n📝 作家团讨论中...\n")
        result = await council.run(topic=topic, writer_ids=writer_ids)

        # Step 7: 保存结果
        self._save_result(book, result, scope)

        return result

    def _select_writers(self, recommended: list[str]) -> list[str]:
        """显示推荐，用户可修改"""
        print("\n✍️ 推荐作家团：")
        for i, wid in enumerate(recommended, 1):
            print(f"  {i}. {wid}")

        print("\n可用作家：")
        all_writers = list(WriterRouter.WRITER_GENRES.keys())
        for i, wid in enumerate(all_writers, 1):
            print(f"  {i}. {wid}")

        choice = input("\n直接回车使用推荐，或输入作家编号（逗号分隔）: ").strip()
        if not choice:
            return recommended

        # 解析用户选择
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        return [all_writers[i] for i in indices if 0 <= i < len(all_writers)]

    def _build_topic(self, theme: ThemeSummary, scope: WritingScope, book: Book) -> str:
        """构建给CouncilOrchestrator的topic"""
        return f"""书籍：{book.name}
类型：{theme.genre}
情绪：{theme.emotion}
主角：{theme.protagonist}
目标：{theme.desire}
冲突：{theme.conflict}
世界观：{theme.setting}
效果：{theme.effect}
场景：{theme.scene or "无"}

写作任务：{scope.description}
写作模式：{scope.mode}
目标范围：{scope.target or "无特定目标"}
"""

    def _save_result(self, book: Book, result: str, scope: WritingScope) -> None:
        """保存结果到书的数据目录"""
        output_dir = self._bookshelf.get_book_data_dir(book.name) / "council"
        output_dir.mkdir(exist_ok=True)

        filename = f"{scope.mode}_{scope.target or 'output'}.md"
        (output_dir / filename).write_text(result, encoding="utf-8")
        print(f"\n💾 已保存到: {output_dir / filename}")
