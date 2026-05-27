# Writer Council: 多作家辩论系统设计

## 概述

为 scribe-py 新增"作家团"模块，模仿 TradingAgents 的多智能体辩论模式，让多位具有不同写作风格的 AI 作家围绕用户的写作需求展开讨论，最终由主编角色裁决输出方案。

## 需求

- **双场景**：审稿（用户提交文本，作家团给修改建议）+ 创作构思（用户描述需求，作家团讨论生成方案）
- **辩论模式**：作家两两/多人对辩，主编裁决（类似 TradingAgents 的 Bull/Bear → Research Manager 模式）
- **作家选择**：系统根据题材推荐 + 用户可覆盖
- **轮次**：固定轮次，默认 2-3 轮
- **主编**：裁决型，综合所有观点后给出最终方案

## 方案选择

**方案B：纯Python异步（scribe-py原生）**

- 零新依赖，复用 scribe-py 现有 AgentLoop + PersonaConfig + Memory 系统
- 辩论循环用纯 Python for 循环实现
- 状态管理用 dataclass

## 模块结构

```
scribe/council/
├── __init__.py
├── council.py          # CouncilOrchestrator - 主编排器
├── debate_state.py     # WriterDebateState - 辩论状态
├── editor.py           # EditorAgent - 主编裁决
├── writer_agent.py     # WriterAgent - 作家代理封装
└── router.py           # WriterRouter - 题材匹配/推荐
```

## 辩论状态

```python
@dataclass
class WriterOpinion:
    writer_id: str          # e.g. "jiulufeixiang"
    writer_name: str        # e.g. "九鹭非香"
    round: int              # 第几轮
    content: str            # 该轮发言内容
    stance: str             # "support" | "oppose" | "neutral" | "suggest"

@dataclass
class WriterDebateState:
    topic: str                          # 讨论主题/用户需求
    user_text: str | None               # 用户提交的文本（审稿场景）
    rounds: int                         # 当前轮次
    max_rounds: int                     # 最大轮次
    writers: list[str]                  # 参与作家ID列表
    history: list[WriterOpinion]        # 全部发言记录
    per_writer_history: dict[str, list[str]]  # 按作家分组的历史
    current_response: str               # 最新一条发言
    final_proposal: str | None          # 主编最终方案
```

与 TradingAgents 的字符串拼接不同，使用结构化 `WriterOpinion` 列表，方便按作家/轮次检索。

## 配置

```python
@dataclass
class CouncilConfig:
    max_rounds: int = 2                        # 默认辩论轮次
    model: str = "gpt-4o"                      # 使用的模型
    editor_persona: PersonaConfig | None = None # 自定义主编人格（可选）
    writer_dir: Path = Path("writers/")         # 作家SKILL.md目录
```

## WriterAgent 封装

```python
class WriterAgent:
    """将 AgentLoop + PersonaConfig + 辩论prompt 组合在一起"""

    def __init__(self, writer_id: str, llm: LlmDriver, persona_path: Path):
        self.writer_id = writer_id
        self._persona = PersonaLoader.load(persona_path)
        self._agent = AgentLoop(llm).with_persona(self._persona)

    async def debate(self, state: WriterDebateState, session_id: str, model: str) -> WriterOpinion:
        prompt = self._build_debate_prompt(state)
        conversation = [Message(role=Role.USER, content=prompt)]
        content = await self._agent.run(session_id, conversation, model)
        return WriterOpinion(
            writer_id=self.writer_id,
            writer_name=self._persona.name,
            round=state.rounds,
            content=content,
            stance=self._extract_stance(content),
        )
```

- `session_id` 由 CouncilOrchestrator 在 run() 开始时生成，透传给所有作家
- `model` 从 CouncilConfig 读取，透传给所有作家
- PersonaLoader 复用 scribe-py 已有的，从 writers/ 文件夹加载 SKILL.md
- `_build_debate_prompt` 注入：辩论主题、用户文本、自己的历史、其他作家的最新发言
- `_extract_stance` 用简单规则从内容中提取立场标签

## EditorAgent 主编裁决

```python
class EditorAgent:
    """裁决型主编 — 综合所有辩论内容，产出最终方案"""

    def __init__(self, llm: LlmDriver, editor_persona: PersonaConfig | None = None):
        self._agent = AgentLoop(llm).with_persona(editor_persona or self._default_editor())

    async def synthesize(self, state: WriterDebateState, session_id: str, model: str) -> str:
        prompt = self._build_synthesis_prompt(state)
        conversation = [Message(role=Role.USER, content=prompt)]
        return await self._agent.run(session_id, conversation, model)
```

主编默认无人格，用通用 system prompt。用户可通过 `editor_persona` 自定义主编风格。

裁决 prompt 注入：用户需求 + 全部辩论记录 + 结构化输出指令（共识/分歧/最终方案）。

## CouncilOrchestrator 主编排器

```python
class CouncilOrchestrator:
    """主编排器 — 管理整个辩论流程"""

    def __init__(self, llm: LlmDriver, config: CouncilConfig):
        self._llm = llm
        self._config = config
        self._writers: dict[str, WriterAgent] = {}
        self._editor = EditorAgent(llm, config.editor_persona)

    def register_writer(self, writer_id: str, persona_path: Path):
        self._writers[writer_id] = WriterAgent(writer_id, self._llm, persona_path)

    async def run(
        self,
        topic: str,
        writer_ids: list[str],
        user_text: str | None = None,
        max_rounds: int | None = None,
    ) -> str:
        session_id = new_session_id()  # 复用 scribe.types 中的 new_session_id
        rounds = max_rounds or self._config.max_rounds
        model = self._config.model

        state = WriterDebateState(
            topic=topic, user_text=user_text,
            rounds=0, max_rounds=rounds,
            writers=writer_ids, history=[],
            per_writer_history={wid: [] for wid in writer_ids},
            current_response="", final_proposal=None,
        )

        for round_num in range(rounds):
            state.rounds = round_num + 1
            for wid in writer_ids:
                writer = self._writers[wid]
                opinion = await writer.debate(state, session_id, model)
                state.history.append(opinion)
                state.per_writer_history[wid].append(opinion.content)
                state.current_response = opinion.content

        state.final_proposal = await self._editor.synthesize(state, session_id, model)
        return state.final_proposal
```

核心流程：`注册作家 → for round → for writer → 辩论 → 主编裁决`

与 TradingAgents 的区别：
- TradingAgents 用 LangGraph 条件路由，我们用嵌套 for 循环
- TradingAgents 的 Bull/Bear 是固定对立角色，我们的作家是平等讨论
- 状态更新方式不同，但信息流一致

## WriterRouter 题材匹配

```python
class WriterRouter:
    """根据用户输入推荐最相关的作家组合"""

    WRITER_GENRES = {
        "jiulufeixiang":     {"仙侠", "言情", "古装", "轻喜剧", "虐心"},
        "mo-xiang-tong-xiu": {"仙侠", "耽美", "群像", "反派设计", "暗黑"},
        "priest":            {"科幻", "蒸汽朋克", "西幻", "刑侦", "悬疑", "反乌托邦", "深度"},
        "san-san":           {"纯文学", "短篇", "现实主义", "哲学", "女性"},
        "liu-cui-hu":        {"都市", "职场", "情感", "现实题材", "女性"},
        "mei-shi-niang":     {"现实题材", "历史", "小人物", "长篇", "温暖"},
    }

    COMBO_SUGGESTIONS = {
        "仙侠":  ["jiulufeixiang", "mo-xiang-tong-xiu"],
        "都市":  ["liu-cui-hu", "mei-shi-niang"],
        "现实":  ["mei-shi-niang", "san-san", "liu-cui-hu"],
        "言情":  ["jiulufeixiang", "liu-cui-hu"],
        "纯文学": ["san-san", "mei-shi-niang"],
        "科幻":  ["priest", "mo-xiang-tong-xiu"],
        "悬疑":  ["priest", "liu-cui-hu"],
        "西幻":  ["priest", "mo-xiang-tong-xiu"],
    }

    def recommend(self, topic: str, user_text: str | None = None) -> list[str]:
        scores = {wid: 0 for wid in self.WRITER_GENRES}
        combined = topic + (user_text or "")
        for wid, genres in self.WRITER_GENRES.items():
            for genre in genres:
                if genre in combined:
                    scores[wid] += 1
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top = [wid for wid, score in ranked if score > 0][:3]
        if len(top) < 2:
            top = [wid for wid, _ in ranked[:2]]
        return top
```

简单关键词匹配做推荐，用户可覆盖。兜底保证至少 2 位作家参与辩论。

## 参与作家

| ID | 名字 | 擅长题材 |
|----|------|---------|
| jiulufeixiang | 九鹭非香 | 仙侠、言情、古装、轻喜剧、虐心 |
| mo-xiang-tong-xiu | 墨香铜臭 | 仙侠、耽美、群像、反派设计、暗黑 |
| priest | Priest | 科幻、蒸汽朋克、西幻、刑侦、悬疑、反乌托邦、深度 |
| san-san | 三三 | 纯文学、短篇、现实主义、哲学、女性 |
| liu-cui-hu | 柳翠虎 | 都市、职场、情感、现实题材、女性 |
| mei-shi-niang | 眉师娘 | 现实题材、历史、小人物、长篇、温暖 |

每位作家的人格定义在 `writers/` 目录下的 SKILL.md 文件中，通过 PersonaLoader 加载。

## 数据流

```
用户输入 (topic + user_text?)
    ↓
WriterRouter.recommend() → 推荐作家ID列表
    ↓
用户确认/覆盖 → 最终作家ID列表
    ↓
CouncilOrchestrator.run()
    ├─ 生成 session_id (new_session_id())
    ├─ 读取 model (CouncilConfig.model)
    ↓
┌─ Round 1: Writer_A.debate(state, sid, model) → Writer_B.debate(...) → Writer_C.debate(...)
├─ Round 2: Writer_A.debate(...) → Writer_B.debate(...) → Writer_C.debate(...)
└─ ...
    ↓
EditorAgent.synthesize(全部辩论记录, sid, model) → 最终方案
    ↓
输出给用户
```

## 依赖

- 无新外部依赖
- 复用 scribe-py 现有模块：AgentLoop, PersonaConfig, PersonaLoader, Message, Role
- writers/ 目录下的 SKILL.md 文件作为作家人格定义
