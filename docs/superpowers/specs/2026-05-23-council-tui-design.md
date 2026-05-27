# Writer Council TUI 设计

## 概述

为 scribe-py 的 Writer Council 模块添加向导式TUI交互，集成到现有CLI流程中。用户选书后自动进入作家团工作流：主题问答→选作家→输入范围→辩论+写作。

## 需求

1. **书架功能**：选书籍（已有，复用）
2. **选作家**：系统推荐+用户可覆盖
3. **主题确定**：多轮问答（5-8题），类似grill-me风格
4. **选作家团**：根据主题推荐但不强制
5. **写作范围**：自由输入解析（大纲/第X章/卷X/整本）
6. **切换LLM**：已有 `/model` 命令（复用）

## 方案选择

**方案B：向导式流程** — 选书后自动运行线性向导，逐步收集信息，最后执行。

## 整体流程

```
scribe run
    ↓
选书（已有 _select_book_interactive）
    ↓
🎯 主题问答（5-8题）
    Q1: 你想写什么类型？（仙侠/都市/科幻/纯文学/历史/...）
    Q2: 故事的核心情绪是什么？（热血/虐心/温暖/悬疑/...）
    Q3: 主角是什么样的人？（身份/性格/缺陷）
    Q4: 主角最想要什么？（目标/执念）
    Q5: 最大的冲突是什么？（人vs人/人vs命运/人vs自我）
    Q6: 故事发生在哪里？（世界观/时代/地点）
    Q7: 你想达到什么效果？（让读者笑/哭/思考/紧张）
    Q8: 有什么特别想写的场景或画面吗？
    ↓
汇总主题摘要 → 用户确认
    ↓
✍️ 选作家（推荐2-3位 + 用户可改）
    ↓
📐 输入写作范围（"写大纲" / "写第3章" / "写到第10章" / "写整本"）
    ↓
📝 作家团辩论 → 主编裁决 → 生成文本
    ↓
输出结果（保存到书的数据目录）
```

## 模块结构

```
scribe/council/
├── __init__.py          (已有，更新导出)
├── council.py           (已有 - CouncilOrchestrator)
├── debate_state.py      (已有 - WriterDebateState)
├── editor.py            (已有 - EditorAgent)
├── router.py            (已有 - WriterRouter)
├── writer_agent.py      (已有 - WriterAgent)
└── wizard.py            (新增)
    ├── ThemeInterviewer  # 主题问答
    ├── ScopeParser       # 范围解析
    ├── ThemeSummary      # 主题摘要数据结构
    ├── WritingScope      # 写作范围数据结构
    └── CouncilWizard     # 主编排（串联整个流程）
```

修改文件：
- `scribe/cli/main.py` — 选书后自动调用 CouncilWizard
- `scribe/cli/tui.py` — 新增 /council, /writers, /scope, /theme 命令

## ThemeInterviewer 主题问答

```python
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
        answers = {}
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

- 有选项的用选择题，没有的用自由输入
- 空回答可跳过（如Q8场景）
- 最后生成 ThemeSummary，包含结构化数据和汇总文本

## ThemeSummary 主题摘要

```python
@dataclass
class ThemeSummary:
    genre: str
    emotion: str
    protagonist: str
    desire: str
    conflict: str
    setting: str
    effect: str
    scene: str | None

    @property
    def summary(self) -> str:
        """生成汇总文本，供WriterRouter使用"""
        ...

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
  场景：{self.scene or '无'}
""")
            if input("确认？(Y/n) ").strip().lower() != "n":
                return self
            # 重新问答
            self = asyncio.run(interviewer.interview())
```

## ScopeParser 范围解析

```python
@dataclass
class WritingScope:
    mode: str           # "outline" | "chapter" | "volume" | "full"
    target: str | None  # e.g. "第3章", "卷二", None
    description: str    # 人类可读描述

class ScopeParser:
    """解析用户的自由输入为写作范围"""

    def parse(self, user_input: str) -> WritingScope:
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

        # 范围匹配："写到第10章"
        range_match = re.search(r'从?第?(\d+).+到第?(\d+)', text)
        if range_match:
            return WritingScope(mode="chapter", target=text, description=f"生成{text}")

        # 默认：大纲
        return WritingScope(mode="outline", target=None, description="生成大纲")
```

## CouncilWizard 主编排

```python
class CouncilWizard:
    """向导流程 — 选书后自动运行"""

    def __init__(self, llm: LlmDriver, bookshelf: Bookshelf):
        self._llm = llm
        self._bookshelf = bookshelf
        self._router = WriterRouter()
        self._interviewer = ThemeInterviewer()
        self._scope_parser = ScopeParser()

    async def run(self, book: Book) -> str:
        # Step 1: 主题问答
        theme = await self._interviewer.interview()
        theme.confirm(self._interviewer)

        # Step 2: 选作家
        recommended = self._router.recommend(theme.summary)
        writer_ids = self._select_writers(recommended)

        # Step 3: 输入范围
        scope_text = input("📐 你想写什么？（大纲/第X章/整本）: ")
        scope = self._scope_parser.parse(scope_text)

        # Step 4: 初始化Council
        config = CouncilConfig(
            max_rounds=2,
            model=self._get_current_model(),
        )
        council = CouncilOrchestrator(self._llm, config)

        for wid in writer_ids:
            persona_path = Path(f"writers/{wid}-perspective")
            council.register_writer(wid, persona_path)

        # Step 5: 构建主题prompt
        topic = self._build_topic(theme, scope, book)

        # Step 6: 执行辩论+写作
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

## CLI集成

### main.py 修改

```python
@cli.command()
@click.option("--council", is_flag=True, help="跳过向导，直接进入普通TUI")
def run(...):
    # ... 选书逻辑 ...

    if not council and selected_book:
        from scribe.council.wizard import CouncilWizard
        wizard = CouncilWizard(llm, bookshelf)
        result = asyncio.run(wizard.run(selected_book))
        print(result)
        return

    # 普通TUI模式
    mode = InteractiveMode(state, sid)
    mode.run()
```

### tui.py 新增命令

在 `_run_rich()` 和 `_run_fallback()` 中添加：

```python
# /council — 重新执行向导
if text == "/council":
    from scribe.council.wizard import CouncilWizard
    wizard = CouncilWizard(llm, bookshelf)
    result = asyncio.run(wizard.run(book))
    print(result)
    continue

# /writers — 查看当前作家团
if text == "/writers":
    print("当前作家团：")
    for wid in current_writer_ids:
        print(f"  - {wid}")
    continue

# /scope — 查看/修改写作范围
if text.startswith("/scope"):
    if len(text) > 7:
        scope = scope_parser.parse(text[7:])
    print(f"当前范围：{current_scope.description}")
    continue

# /theme — 查看主题摘要
if text == "/theme":
    print(theme.summary)
    continue
```

## 数据流

```
用户输入
    ↓
Bookshelf.select(book)
    ↓
ThemeInterviewer.interview() → ThemeSummary
    ↓
WriterRouter.recommend(summary) → list[writer_id]
    ↓
用户确认/修改 → final writer_ids
    ↓
ScopeParser.parse(user_input) → WritingScope
    ↓
CouncilOrchestrator.run(topic, writer_ids) → final_proposal
    ↓
保存到 book/data/council/{scope.mode}_{scope.target}.md
```

## 依赖

- 无新外部依赖
- 复用：Bookshelf, WriterRouter, CouncilOrchestrator, CouncilConfig
- 新增：ThemeInterviewer, ScopeParser, ThemeSummary, WritingScope, CouncilWizard
