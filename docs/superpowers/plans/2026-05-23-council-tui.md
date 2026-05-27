# Writer Council TUI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Writer Council 添加向导式TUI交互，选书后自动进入主题问答→选作家→输入范围→辩论+写作流程

**Architecture:** 新增 `scribe/council/wizard.py` 包含 ThemeInterviewer、ScopeParser、ThemeSummary、WritingScope、CouncilWizard。修改 `scribe/cli/main.py` 和 `scribe/cli/tui.py` 集成向导流程。

**Tech Stack:** Python 3.12+, scribe-py现有基础设施, click (CLI), rich (TUI)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `scribe/council/wizard.py` | 新增 | ThemeInterviewer, ScopeParser, ThemeSummary, WritingScope, CouncilWizard |
| `tests/council/test_wizard.py` | 新增 | wizard模块测试 |
| `scribe/council/__init__.py` | 修改 | 更新导出 |
| `scribe/cli/main.py` | 修改 | 选书后自动调用CouncilWizard |
| `scribe/cli/tui.py` | 修改 | 新增 /council, /writers, /scope, /theme 命令 |

---

### Task 1: 数据结构 — ThemeSummary + WritingScope

**Files:**
- Create: `scribe/council/wizard.py`（部分）
- Create: `tests/council/test_wizard.py`（部分）

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_wizard.py
import pytest
from scribe.council.wizard import ThemeSummary, WritingScope, ScopeParser


def test_theme_summary_from_answers():
    answers = {
        "genre": "仙侠",
        "emotion": "虐心",
        "protagonist": "魔尊",
        "desire": "自由",
        "conflict": "人与命运",
        "setting": "三界",
        "effect": "让读者哭",
        "scene": "大战后独坐山巅",
    }
    theme = ThemeSummary.from_answers(answers)
    assert theme.genre == "仙侠"
    assert theme.emotion == "虐心"
    assert theme.scene == "大战后独坐山巅"


def test_theme_summary_summary_property():
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    summary = theme.summary
    assert "仙侠" in summary
    assert "魔尊" in summary
    assert "自由" in summary


def test_theme_summary_missing_optional():
    answers = {
        "genre": "都市", "emotion": "温暖", "protagonist": "白领",
        "desire": "成功", "conflict": "人与人", "setting": "上海",
        "effect": "让读者思考",
    }
    theme = ThemeSummary.from_answers(answers)
    assert theme.scene is None


def test_writing_scope_outline():
    scope = WritingScope(mode="outline", target=None, description="生成大纲")
    assert scope.mode == "outline"
    assert scope.target is None


def test_writing_scope_chapter():
    scope = WritingScope(mode="chapter", target="第三章", description="生成第三章")
    assert scope.mode == "chapter"
    assert scope.target == "第三章"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现数据结构**

```python
# scribe/council/wizard.py（部分）
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/wizard.py tests/council/test_wizard.py
git commit -m "feat(council): add ThemeSummary and WritingScope data structures"
```

---

### Task 2: ScopeParser 范围解析

**Files:**
- Modify: `scribe/council/wizard.py`
- Modify: `tests/council/test_wizard.py`

- [ ] **Step 1: 添加测试**

```python
# tests/council/test_wizard.py 追加

def test_scope_parser_outline():
    parser = ScopeParser()
    scope = parser.parse("写大纲")
    assert scope.mode == "outline"
    assert scope.target is None


def test_scope_parser_full():
    parser = ScopeParser()
    scope = parser.parse("整本书")
    assert scope.mode == "full"


def test_scope_parser_chapter_cn():
    parser = ScopeParser()
    scope = parser.parse("第3章")
    assert scope.mode == "chapter"
    assert scope.target == "第3章"


def test_scope_parser_chapter_cn_num():
    parser = ScopeParser()
    scope = parser.parse("第三章")
    assert scope.mode == "chapter"
    assert scope.target == "第三章"


def test_scope_parser_volume():
    parser = ScopeParser()
    scope = parser.parse("卷二")
    assert scope.mode == "volume"
    assert scope.target == "卷二"


def test_scope_parser_range():
    parser = ScopeParser()
    scope = parser.parse("从第3章到第7章")
    assert scope.mode == "chapter"
    assert "第3章" in scope.target
    assert "第7章" in scope.target


def test_scope_parser_default():
    parser = ScopeParser()
    scope = parser.parse("随便写写")
    assert scope.mode == "outline"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: FAIL — ScopeParser not defined

- [ ] **Step 3: 实现 ScopeParser**

```python
# scribe/council/wizard.py 追加

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

        # 章节匹配："第3章", "第三章"
        chapter_match = re.search(r'第(\d+|[一二三四五六七八九十百]+)章', text)
        if chapter_match:
            target = chapter_match.group(0)
            return WritingScope(mode="chapter", target=target, description=f"生成{target}")

        # 卷匹配："卷二", "第二卷"
        volume_match = re.search(r'第?(\d+|[一二三四五六七八九十百]+)卷', text)
        if volume_match:
            target = volume_match.group(0)
            return WritingScope(mode="volume", target=target, description=f"生成{target}")

        # 范围匹配："从第3章到第7章"
        range_match = re.search(r'从?第?(\d+).+到第?(\d+)', text)
        if range_match:
            return WritingScope(mode="chapter", target=text, description=f"生成{text}")

        # 默认：大纲
        return WritingScope(mode="outline", target=None, description="生成大纲")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/wizard.py tests/council/test_wizard.py
git commit -m "feat(council): add ScopeParser for writing scope parsing"
```

---

### Task 3: ThemeInterviewer 主题问答

**Files:**
- Modify: `scribe/council/wizard.py`
- Modify: `tests/council/test_wizard.py`

- [ ] **Step 1: 添加测试**

```python
# tests/council/test_wizard.py 追加

def test_theme_interviewer_questions():
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    assert len(interviewer.QUESTIONS) == 8
    assert interviewer.QUESTIONS[0][0] == "genre"
    assert interviewer.QUESTIONS[7][0] == "scene"


def test_theme_interviewer_ask_choice(capsys):
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    # Mock input
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value='1'):
        result = interviewer._ask_choice("测试问题?", ["选项A", "选项B"])
    assert result == "选项A"


def test_theme_interviewer_ask_text():
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value='测试回答'):
        result = interviewer._ask_text("测试问题?")
    assert result == "测试回答"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: FAIL — ThemeInterviewer not defined

- [ ] **Step 3: 实现 ThemeInterviewer**

```python
# scribe/council/wizard.py 追加

class ThemeInterviewer:
    """通过多轮问答确定写作主题"""

    QUESTIONS = [
        ("genre", "你想写什么类型？", ["仙侠", "都市", "科幻", "纯文学", "历史", "悬疑", "奇幻", "其他"]),
        ("emotion", "故事的核心情绪是什么？", ["热血", "虐心", "温暖", "悬疑", "搞笑", "沉重", "治愈"]),
        ("protagonist", "主角是什么样的人？（身份/性格/缺陷）", None),
        ("desire", "主角最想要什么？（目标/执念）", None),
        ("conflict", "最大的冲突是什么？", ["人与人", "人与命运", "人与自我", "人与社会", "人与自然"]),
        ("setting", "故事发生在哪里？（世界观/时代/地点）", None),
        ("effect", "你想达到什么效果？", ["让读者笑", "让读者哭", "让读者思考", "让读者紧张", "让读者感动"]),
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/wizard.py tests/council/test_wizard.py
git commit -m "feat(council): add ThemeInterviewer for theme Q&A"
```

---

### Task 4: ThemeSummary.confirm() 确认交互

**Files:**
- Modify: `scribe/council/wizard.py`
- Modify: `tests/council/test_wizard.py`

- [ ] **Step 1: 添加测试**

```python
# tests/council/test_wizard.py 追加

def test_theme_summary_confirm_accept(capsys):
    from scribe.council.wizard import ThemeInterviewer
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    interviewer = ThemeInterviewer()
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value=''):
        result = theme.confirm(interviewer)
    assert result is theme


def test_theme_summary_confirm_retry(capsys):
    from scribe.council.wizard import ThemeInterviewer
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    interviewer = ThemeInterviewer()
    import unittest.mock
    # 第一次输入n（不确认），然后重新问答时输入Y
    with unittest.mock.patch('builtins.input', side_effect=['n', '', '', '', '', '', '', '', '', '']):
        with unittest.mock.patch.object(interviewer, 'interview', return_value=theme):
            result = theme.confirm(interviewer)
    assert result is theme
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: FAIL — confirm method not found

- [ ] **Step 3: 实现 confirm 方法**

```python
# 在 ThemeSummary 类中添加

    def confirm(self, interviewer: "ThemeInterviewer") -> ThemeSummary:
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
  场景：{self.scene or '无'}
""")
            if input("确认？(Y/n) ").strip().lower() != "n":
                return self
            # 重新问答
            new_theme = asyncio.run(interviewer.interview())
            self.genre = new_theme.genre
            self.emotion = new_theme.emotion
            self.protagonist = new_theme.protagonist
            self.desire = new_theme.desire
            self.conflict = new_theme.conflict
            self.setting = new_theme.setting
            self.effect = new_theme.effect
            self.scene = new_theme.scene
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/wizard.py tests/council/test_wizard.py
git commit -m "feat(council): add ThemeSummary.confirm() interactive confirmation"
```

---

### Task 5: CouncilWizard 主编排

**Files:**
- Modify: `scribe/council/wizard.py`
- Modify: `tests/council/test_wizard.py`

- [ ] **Step 1: 添加测试**

```python
# tests/council/test_wizard.py 追加

def test_council_wizard_build_topic():
    from scribe.council.wizard import CouncilWizard, ThemeSummary, WritingScope
    from unittest.mock import MagicMock

    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene="大战后独坐山巅",
    )
    scope = WritingScope(mode="chapter", target="第三章", description="生成第三章")
    book = MagicMock()
    book.name = "测试书籍"

    wizard = CouncilWizard.__new__(CouncilWizard)
    topic = wizard._build_topic(theme, scope, book)

    assert "测试书籍" in topic
    assert "仙侠" in topic
    assert "魔尊" in topic
    assert "第三章" in topic
    assert "chapter" in topic


def test_council_wizard_select_writers_default():
    from scribe.council.wizard import CouncilWizard
    import unittest.mock

    wizard = CouncilWizard.__new__(CouncilWizard)
    recommended = ["jiulufeixiang", "priest"]

    with unittest.mock.patch('builtins.input', return_value=''):
        result = wizard._select_writers(recommended)
    assert result == recommended


def test_council_wizard_select_writers_custom():
    from scribe.council.wizard import CouncilWizard
    import unittest.mock

    wizard = CouncilWizard.__new__(CouncilWizard)
    recommended = ["jiulufeixiang", "priest"]

    with unittest.mock.patch('builtins.input', return_value='3,4'):
        result = wizard._select_writers(recommended)
    assert "san-san" in result
    assert "liu-cui-hu" in result
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: FAIL — CouncilWizard not defined

- [ ] **Step 3: 实现 CouncilWizard**

```python
# scribe/council/wizard.py 追加

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
        print(f"\n✍️ 推荐作家团：")
        for i, wid in enumerate(recommended, 1):
            print(f"  {i}. {wid}")

        print(f"\n可用作家：")
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
场景：{theme.scene or '无'}

写作任务：{scope.description}
写作模式：{scope.mode}
目标范围：{scope.target or '无特定目标'}
"""

    def _save_result(self, book: Book, result: str, scope: WritingScope) -> None:
        """保存结果到书的数据目录"""
        output_dir = self._bookshelf.get_book_data_dir(book.name) / "council"
        output_dir.mkdir(exist_ok=True)

        filename = f"{scope.mode}_{scope.target or 'output'}.md"
        (output_dir / filename).write_text(result, encoding="utf-8")
        print(f"\n💾 已保存到: {output_dir / filename}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_wizard.py -v`
Expected: PASS

- [ ] **Step 5: 更新模块导出**

```python
# scribe/council/__init__.py 追加

from scribe.council.wizard import (
    ThemeInterviewer,
    ScopeParser,
    ThemeSummary,
    WritingScope,
    CouncilWizard,
)

__all__ = [
    # ... 已有导出 ...
    "ThemeInterviewer",
    "ScopeParser",
    "ThemeSummary",
    "WritingScope",
    "CouncilWizard",
]
```

- [ ] **Step 6: Commit**

```bash
git add scribe/council/wizard.py scribe/council/__init__.py tests/council/test_wizard.py
git commit -m "feat(council): add CouncilWizard orchestrator"
```

---

### Task 6: CLI集成 — main.py

**Files:**
- Modify: `scribe/cli/main.py`

- [ ] **Step 1: 添加 --council 选项**

在 `run` 命令中添加 `--council` 选项：

```python
@cli.command()
@click.option("-p", "--prompt", help="Single-shot prompt (non-interactive)")
@click.option("-s", "--session", "session_id", help="Resume a specific session by ID prefix")
@click.option("--list-sessions", is_flag=True, help="List all saved sessions")
@click.option("--model", help="Model override for this invocation")
@click.option("--book", help="Book name to open (skips selection prompt)")
@click.option("--new-book", help="Create a new book and open it")
@click.option("--list-books", is_flag=True, help="List all books on the bookshelf")
@click.option("--council", is_flag=True, help="跳过向导，直接进入普通TUI")
def run(
    prompt: str | None,
    session_id: str | None,
    list_sessions: bool,
    model: str | None,
    book: str | None,
    new_book: str | None,
    list_books: bool,
    council: bool,
) -> None:
```

- [ ] **Step 2: 修改选书后逻辑**

在 `run` 函数中，选书完成后、初始化 state 之前，添加向导逻辑：

```python
    # 选书完成后
    if selected_book and not council:
        # 向导模式
        from scribe.council.wizard import CouncilWizard
        # 创建LLM（简化版，实际需要从config读取）
        from scribe.llm import create_llm
        cfg = asyncio.run(_load_config())
        llm = create_llm(cfg["provider"], cfg["model"])
        wizard = CouncilWizard(llm, bookshelf)
        result = asyncio.run(wizard.run(selected_book))
        print(result)
        return
```

- [ ] **Step 3: 运行测试确认无回归**

Run: `rtk python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add scribe/cli/main.py
git commit -m "feat(cli): integrate CouncilWizard into run command"
```

---

### Task 7: TUI命令 — tui.py

**Files:**
- Modify: `scribe/cli/tui.py`

- [ ] **Step 1: 在 _run_fallback 中添加命令**

在 `/switch` 处理之后、"Regular message" 之前添加：

```python
            if text == "/council":
                from scribe.council.wizard import CouncilWizard
                from scribe.bookshelf import Bookshelf
                bookshelf = Bookshelf()
                book = bookshelf.get_active()
                if not book:
                    print("  请先选书：/book <书名>")
                    continue
                # 需要llm实例 — 从state获取
                llm = self.state._llm  # 假设state有_llm属性
                wizard = CouncilWizard(llm, bookshelf)
                result = asyncio.run(wizard.run(book))
                print(result)
                continue

            if text == "/writers":
                print("  当前作家团：")
                # 从session上下文读取
                print("  （需要在向导执行后保存到session）")
                continue

            if text.startswith("/scope"):
                parts = text.split(" ", 1)
                if len(parts) > 1:
                    from scribe.council.wizard import ScopeParser
                    parser = ScopeParser()
                    scope = parser.parse(parts[1])
                    print(f"  范围：{scope.description}")
                else:
                    print("  用法：/scope <范围>")
                    print("  示例：/scope 第3章  /scope 大纲  /scope 整本")
                continue

            if text == "/theme":
                print("  主题摘要：")
                print("  （需要在向导执行后保存到session）")
                continue
```

- [ ] **Step 2: 更新 /help 命令**

在 help 输出中添加新命令：

```python
                print("  /council       重新执行作家团向导")
                print("  /writers       查看当前作家团")
                print("  /scope <范围>  查看/设置写作范围")
                print("  /theme         查看主题摘要")
```

- [ ] **Step 3: 在 _run_rich 中添加相同命令**

复制 _run_fallback 中的命令处理逻辑到 _run_rich 方法中，使用 rich console 输出。

- [ ] **Step 4: 运行测试确认无回归**

Run: `rtk python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/cli/tui.py
git commit -m "feat(tui): add /council, /writers, /scope, /theme commands"
```

---

### Task 8: 全量测试 + 类型检查

**Files:**
- None (verification only)

- [ ] **Step 1: 运行全部 council 测试**

Run: `rtk python -m pytest tests/council/ -v`
Expected: ALL PASS

- [ ] **Step 2: 运行 mypy 类型检查**

Run: `rtk python -m mypy scribe/council/ --ignore-missing-imports`
Expected: No errors in council code

- [ ] **Step 3: 运行全量测试**

Run: `rtk python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore(council): pass all tests and type checks"
```
