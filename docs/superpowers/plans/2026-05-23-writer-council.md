# Writer Council 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 scribe-py 新增作家团辩论模块，让多位AI作家围绕写作需求讨论并输出方案

**Architecture:** 纯Python异步，复用scribe-py现有AgentLoop+PersonaConfig。新建scribe/council/模块，包含辩论状态、作家代理、主编裁决、题材路由、主编排器五个组件。

**Tech Stack:** Python 3.12+, scribe-py现有基础设施, writers/目录下的SKILL.md人格文件

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `scribe/council/__init__.py` | 模块导出 |
| `scribe/council/debate_state.py` | WriterOpinion + WriterDebateState 数据结构 |
| `scribe/council/writer_agent.py` | WriterAgent — 作家代理封装，构建辩论prompt，调用AgentLoop |
| `scribe/council/editor.py` | EditorAgent — 主编裁决，综合辩论记录输出最终方案 |
| `scribe/council/router.py` | WriterRouter — 题材关键词匹配，推荐作家组合 |
| `scribe/council/council.py` | CouncilOrchestrator — 主编排器，管理辩论流程 |
| `tests/council/__init__.py` | 测试包 |
| `tests/council/test_debate_state.py` | 辩论状态测试 |
| `tests/council/test_router.py` | 题材路由测试 |
| `tests/council/test_writer_agent.py` | 作家代理测试 |
| `tests/council/test_editor.py` | 主编裁决测试 |
| `tests/council/test_council.py` | 集成测试 |

---

### Task 1: 辩论状态数据结构

**Files:**
- Create: `scribe/council/__init__.py`
- Create: `scribe/council/debate_state.py`
- Create: `tests/council/__init__.py`
- Create: `tests/council/test_debate_state.py`

- [ ] **Step 1: 创建测试文件**

```python
# tests/council/__init__.py
```

```python
# tests/council/test_debate_state.py
import pytest
from scribe.council.debate_state import WriterOpinion, WriterDebateState


def test_writer_opinion_creation():
    op = WriterOpinion(
        writer_id="jiulufeixiang",
        writer_name="九鹭非香",
        round=1,
        content="我觉得这个角色需要更多背景",
        stance="suggest",
    )
    assert op.writer_id == "jiulufeixiang"
    assert op.round == 1
    assert op.stance == "suggest"


def test_debate_state_creation():
    state = WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是一个仙侠世界的魔尊",
        rounds=0,
        max_rounds=2,
        writers=["jiulufeixiang", "mo-xiang-tong-xiu"],
        history=[],
        per_writer_history={"jiulufeixiang": [], "mo-xiang-tong-xiu": []},
        current_response="",
        final_proposal=None,
    )
    assert state.max_rounds == 2
    assert len(state.writers) == 2
    assert state.final_proposal is None


def test_debate_state_update():
    state = WriterDebateState(
        topic="test",
        user_text=None,
        rounds=0,
        max_rounds=2,
        writers=["a", "b"],
        history=[],
        per_writer_history={"a": [], "b": []},
        current_response="",
        final_proposal=None,
    )
    op = WriterOpinion(
        writer_id="a", writer_name="Writer A",
        round=1, content="test opinion", stance="support",
    )
    state.history.append(op)
    state.per_writer_history["a"].append(op.content)
    state.current_response = op.content
    state.rounds = 1

    assert len(state.history) == 1
    assert state.per_writer_history["a"] == ["test opinion"]
    assert state.current_response == "test opinion"
    assert state.rounds == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_debate_state.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 创建模块和数据结构**

```python
# scribe/council/__init__.py
"""Writer Council — 多作家辩论系统"""

from scribe.council.debate_state import WriterOpinion, WriterDebateState

__all__ = ["WriterOpinion", "WriterDebateState"]
```

```python
# scribe/council/debate_state.py
"""辩论状态数据结构"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WriterOpinion:
    """单个作家的一轮发言"""

    writer_id: str          # e.g. "jiulufeixiang"
    writer_name: str        # e.g. "九鹭非香"
    round: int              # 第几轮
    content: str            # 该轮发言内容
    stance: str             # "support" | "oppose" | "neutral" | "suggest"


@dataclass
class WriterDebateState:
    """辩论全局状态"""

    topic: str                                    # 讨论主题/用户需求
    user_text: str | None                         # 用户提交的文本（审稿场景）
    rounds: int                                   # 当前轮次
    max_rounds: int                               # 最大轮次
    writers: list[str]                            # 参与作家ID列表
    history: list[WriterOpinion] = field(default_factory=list)
    per_writer_history: dict[str, list[str]] = field(default_factory=dict)
    current_response: str = ""                    # 最新一条发言
    final_proposal: str | None = None             # 主编最终方案
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_debate_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/__init__.py scribe/council/debate_state.py tests/council/
git commit -m "feat(council): add debate state data structures"
```

---

### Task 2: WriterRouter 题材匹配

**Files:**
- Create: `scribe/council/router.py`
- Create: `tests/council/test_router.py`

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_router.py
import pytest
from scribe.council.router import WriterRouter


@pytest.fixture
def router():
    return WriterRouter()


def test_recommend_xianxia(router):
    result = router.recommend("帮我写一段仙侠小说的开头")
    assert "jiulufeixiang" in result or "mo-xiang-tong-xiu" in result


def test_recommend_urban(router):
    result = router.recommend("写一个都市职场故事")
    assert "liu-cui-hu" in result or "mei-shi-niang" in result


def test_recommend_scifi(router):
    result = router.recommend("科幻题材的创作构思")
    assert "priest" in result


def test_recommend_pure_literature(router):
    result = router.recommend("纯文学短篇小说")
    assert "san-san" in result


def test_recommend_with_user_text(router):
    result = router.recommend("帮我看看", "这是一个关于仙侠和言情的故事")
    assert "jiulufeixiang" in result


def test_recommend_minimum_two(router):
    result = router.recommend("随便什么题材")
    assert len(result) >= 2


def test_recommend_max_three(router):
    result = router.recommend("仙侠言情古装轻喜剧虐心")
    assert len(result) <= 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_router.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 WriterRouter**

```python
# scribe/council/router.py
"""题材匹配 — 根据用户输入推荐作家组合"""

from __future__ import annotations


class WriterRouter:
    """根据用户输入推荐最相关的作家组合"""

    WRITER_GENRES: dict[str, set[str]] = {
        "jiulufeixiang":     {"仙侠", "言情", "古装", "轻喜剧", "虐心"},
        "mo-xiang-tong-xiu": {"仙侠", "耽美", "群像", "反派设计", "暗黑"},
        "priest":            {"科幻", "蒸汽朋克", "西幻", "刑侦", "悬疑", "反乌托邦", "深度"},
        "san-san":           {"纯文学", "短篇", "现实主义", "哲学", "女性"},
        "liu-cui-hu":        {"都市", "职场", "情感", "现实题材", "女性"},
        "mei-shi-niang":     {"现实题材", "历史", "小人物", "长篇", "温暖"},
    }

    COMBO_SUGGESTIONS: dict[str, list[str]] = {
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
        """根据主题和文本内容推荐作家ID列表"""
        scores: dict[str, int] = {wid: 0 for wid in self.WRITER_GENRES}
        combined = topic + (user_text or "")

        for wid, genres in self.WRITER_GENRES.items():
            for genre in genres:
                if genre in combined:
                    scores[wid] += 1

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top = [wid for wid, score in ranked if score > 0][:3]

        # 兜底：至少选2位
        if len(top) < 2:
            top = [wid for wid, _ in ranked[:2]]

        return top
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/router.py tests/council/test_router.py
git commit -m "feat(council): add WriterRouter for genre-based writer recommendation"
```

---

### Task 3: WriterAgent 作家代理

**Files:**
- Create: `scribe/council/writer_agent.py`
- Create: `tests/council/test_writer_agent.py`

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_writer_agent.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from scribe.council.writer_agent import WriterAgent
from scribe.council.debate_state import WriterDebateState, WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="测试发言内容", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def sample_state():
    return WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是一个仙侠世界的魔尊",
        rounds=1,
        max_rounds=2,
        writers=["test_writer"],
        history=[],
        per_writer_history={"test_writer": []},
        current_response="",
        final_proposal=None,
    )


def test_extract_stance_support():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我同意这个观点，说得很好") == "support"


def test_extract_stance_oppose():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我反对，这样写不行") == "oppose"


def test_extract_stance_suggest():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我建议可以试试另一种写法") == "suggest"


def test_extract_stance_neutral():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("这个角色还行吧") == "neutral"


def test_build_debate_prompt_contains_topic(mock_llm, sample_state):
    agent = WriterAgent.__new__(WriterAgent)
    agent.writer_id = "test"
    agent._persona = MagicMock()
    agent._persona.name = "Test Writer"

    prompt = agent._build_debate_prompt(sample_state)
    assert "帮我看看这个角色" in prompt
    assert "仙侠世界的魔尊" in prompt
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_writer_agent.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 WriterAgent**

```python
# scribe/council/writer_agent.py
"""作家代理 — 将 AgentLoop + PersonaConfig + 辩论prompt 组合"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.types import Message, Role, SessionId
from scribe.agent.loop import AgentLoop
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
        self._agent = AgentLoop(llm).with_persona(persona)

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
            writer_name=self._persona.name,
            round=state.rounds,
            content=content,
            stance=self._extract_stance(content),
        )

    def _build_debate_prompt(self, state: WriterDebateState) -> str:
        """构建辩论prompt"""
        parts = []

        # 角色说明
        parts.append(f"你现在以「{self._persona.name}」的身份参与一场写作讨论。")

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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_writer_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/writer_agent.py tests/council/test_writer_agent.py
git commit -m "feat(council): add WriterAgent for debate participation"
```

---

### Task 4: EditorAgent 主编裁决

**Files:**
- Create: `scribe/council/editor.py`
- Create: `tests/council/test_editor.py`

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_editor.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from scribe.council.editor import EditorAgent
from scribe.council.debate_state import WriterDebateState, WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="最终方案：...", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def debate_state_with_history():
    state = WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是魔尊",
        rounds=2,
        max_rounds=2,
        writers=["a", "b"],
        history=[
            WriterOpinion(writer_id="a", writer_name="Writer A", round=1, content="观点A1", stance="suggest"),
            WriterOpinion(writer_id="b", writer_name="Writer B", round=1, content="观点B1", stance="support"),
            WriterOpinion(writer_id="a", writer_name="Writer A", round=2, content="观点A2", stance="oppose"),
            WriterOpinion(writer_id="b", writer_name="Writer B", round=2, content="观点B2", stance="neutral"),
        ],
        per_writer_history={"a": ["观点A1", "观点A2"], "b": ["观点B1", "观点B2"]},
        current_response="观点B2",
        final_proposal=None,
    )
    return state


def test_build_synthesis_prompt_contains_all_opinions(debate_state_with_history):
    editor = EditorAgent.__new__(EditorAgent)
    prompt = editor._build_synthesis_prompt(debate_state_with_history)
    assert "观点A1" in prompt
    assert "观点B1" in prompt
    assert "观点A2" in prompt
    assert "观点B2" in prompt


def test_build_synthesis_prompt_contains_topic(debate_state_with_history):
    editor = EditorAgent.__new__(EditorAgent)
    prompt = editor._build_synthesis_prompt(debate_state_with_history)
    assert "帮我看看这个角色" in prompt
    assert "主角是魔尊" in prompt


def test_build_synthesis_prompt_no_user_text():
    editor = EditorAgent.__new__(EditorAgent)
    state = WriterDebateState(
        topic="创作构思", user_text=None,
        rounds=1, max_rounds=1, writers=["a"],
        history=[WriterOpinion(writer_id="a", writer_name="A", round=1, content="test", stance="suggest")],
        per_writer_history={"a": ["test"]},
        current_response="test", final_proposal=None,
    )
    prompt = editor._build_synthesis_prompt(state)
    assert "（无" in prompt
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_editor.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 EditorAgent**

```python
# scribe/council/editor.py
"""主编裁决 — 综合辩论内容产出最终方案"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from scribe.types import Message, Role, SessionId, PersonaConfig
from scribe.agent.loop import AgentLoop
from scribe.council.debate_state import WriterDebateState

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
        self._agent = AgentLoop(llm).with_persona(editor_persona)

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
            parts.append(f"\n### 【{op.writer_name}·第{op.round}轮·{op.stance}】\n{op.content}")

        # 裁决指令
        parts.append("""
## 你的任务

请综合以上所有作家的讨论，产出最终方案：

1. **共识要点**：哪些观点得到了多位作家的认同？
2. **分歧分析**：存在哪些争议？你倾向于哪一方？为什么？
3. **最终方案**：一个完整的、可直接执行的写作建议或修改方案

请用清晰的结构化格式输出。""")

        return "\n".join(parts)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_editor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/editor.py tests/council/test_editor.py
git commit -m "feat(council): add EditorAgent for debate synthesis"
```

---

### Task 5: CouncilOrchestrator 主编排器

**Files:**
- Create: `scribe/council/council.py`
- Create: `tests/council/test_council.py`

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_council.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from scribe.council.council import CouncilOrchestrator, CouncilConfig
from scribe.council.debate_state import WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="测试内容", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def council_config():
    return CouncilConfig(
        max_rounds=2,
        model="test-model",
        writer_dir=Path("writers/"),
    )


def test_council_config_defaults():
    config = CouncilConfig()
    assert config.max_rounds == 2
    assert config.model == "gpt-4o"


def test_register_writer(mock_llm, council_config, tmp_path):
    council = CouncilOrchestrator(mock_llm, council_config)
    # 注册作家应该不报错
    council.register_writer("test", tmp_path)
    assert "test" in council._writers


@pytest.mark.asyncio
async def test_council_run(mock_llm, council_config):
    """集成测试：模拟完整辩论流程"""
    council = CouncilOrchestrator(mock_llm, council_config)

    # Mock WriterAgent
    mock_writer = MagicMock()
    mock_writer.debate = AsyncMock(return_value=WriterOpinion(
        writer_id="test", writer_name="Test",
        round=1, content="test opinion", stance="suggest",
    ))
    mock_writer.writer_id = "test"
    council._writers["test"] = mock_writer

    # Mock EditorAgent
    council._editor.synthesize = AsyncMock(return_value="最终方案")

    result = await council.run(
        topic="测试主题",
        writer_ids=["test"],
        max_rounds=1,
    )

    assert result == "最终方案"
    assert mock_writer.debate.call_count == 1
    council._editor.synthesize.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_council.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 CouncilConfig 和 CouncilOrchestrator**

```python
# scribe/council/council.py
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_council.py -v`
Expected: PASS

- [ ] **Step 5: 更新模块导出**

```python
# scribe/council/__init__.py
"""Writer Council — 多作家辩论系统"""

from scribe.council.debate_state import WriterOpinion, WriterDebateState
from scribe.council.router import WriterRouter
from scribe.council.writer_agent import WriterAgent
from scribe.council.editor import EditorAgent
from scribe.council.council import CouncilOrchestrator, CouncilConfig

__all__ = [
    "WriterOpinion",
    "WriterDebateState",
    "WriterRouter",
    "WriterAgent",
    "EditorAgent",
    "CouncilOrchestrator",
    "CouncilConfig",
]
```

- [ ] **Step 6: 运行全部测试**

Run: `rtk python -m pytest tests/council/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add scribe/council/council.py scribe/council/__init__.py tests/council/test_council.py
git commit -m "feat(council): add CouncilOrchestrator for debate orchestration"
```

---

### Task 6: SKILL.md 人格加载适配

**Files:**
- Modify: `scribe/council/writer_agent.py`
- Create: `tests/council/test_skill_loader.py`

PersonaLoader 期望 `identity.md` + `ishiki.md`，但 writers/ 下是 SKILL.md。需要一个适配层从 SKILL.md 提取人格信息。

- [ ] **Step 1: 创建测试**

```python
# tests/council/test_skill_loader.py
import pytest
from pathlib import Path

from scribe.council.writer_agent import load_writer_persona


def test_load_writer_persona_from_skill_md(tmp_path):
    """测试从SKILL.md加载作家人格"""
    skill_content = """---
name: test-perspective
description: 测试作家的创作方法论
---

# 测试作家 · 创作思维操作系统

> "测试引言"

## 身份卡

**我是谁**：我叫测试作家，擅长写测试内容。
**我的起点**：从测试开始写作。
**我现在在做什么**：还在测试。

## 核心心智模型

### 模型1: 测试模型
**一句话**：这是一个测试模型。

## 表达DNA

- **句式**：短句为主
- **词汇**：高频使用测试词汇
"""
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(skill_content, encoding="utf-8")

    persona = load_writer_persona(tmp_path)
    assert persona.identity is not None
    assert "测试作家" in persona.identity
    assert persona.ishiki is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `rtk python -m pytest tests/council/test_skill_loader.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 SKILL.md 人格加载**

在 `writer_agent.py` 中添加：

```python
def load_writer_persona(writer_dir: Path) -> PersonaConfig:
    """从 writers/ 目录加载作家人格（SKILL.md 格式）

    SKILL.md 包含完整的人格定义，我们将其拆分为 identity 和 ishiki 两部分。
    """
    skill_path = writer_dir / "SKILL.md"
    if not skill_path.exists():
        # 兼容九鹭非香的旧格式（直接用 .md 文件）
        md_files = list(writer_dir.glob("*.md"))
        if md_files:
            skill_path = md_files[0]
        else:
            raise FileNotFoundError(f"No SKILL.md or .md found in {writer_dir}")

    content = skill_path.read_text(encoding="utf-8")

    # 提取 YAML frontmatter 中的 name
    name = writer_dir.name
    if content.startswith("---"):
        end = content.index("---", 3)
        frontmatter = content[3:end]
        for line in frontmatter.split("\n"):
            if line.strip().startswith("name:"):
                name = line.split(":", 1)[1].strip()
                break

    # 拆分：frontmatter 之后的内容作为 identity
    # 表达DNA、决策启发式等作为 ishiki（说话风格）
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else content

    # 提取身份卡和核心模型作为 identity
    identity_sections = []
    ishiki_sections = []

    current_section = "identity"
    for section in body.split("\n## "):
        section_lower = section.lower()
        if any(k in section_lower for k in ["身份卡", "核心心智模型", "人物时间线", "价值观"]):
            identity_sections.append("## " + section)
        elif any(k in section_lower for k in ["表达dna", "决策启发式", "回答工作流", "角色扮演"]):
            ishiki_sections.append("## " + section)
        else:
            identity_sections.append("## " + section)

    identity = f"# {name}\n\n" + "\n".join(identity_sections)
    ishiki = "\n".join(ishiki_sections) if ishiki_sections else ""

    return PersonaConfig(
        identity=identity,
        ishiki=ishiki,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `rtk python -m pytest tests/council/test_skill_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scribe/council/writer_agent.py tests/council/test_skill_loader.py
git commit -m "feat(council): add SKILL.md persona loader for writer agents"
```

---

### Task 7: 全量测试 + 类型检查

**Files:**
- Modify: `pyproject.toml` (如需)

- [ ] **Step 1: 运行全部 council 测试**

Run: `rtk python -m pytest tests/council/ -v`
Expected: ALL PASS

- [ ] **Step 2: 运行 mypy 类型检查**

Run: `rtk python -m mypy scribe/council/ --ignore-missing-imports`
Expected: No errors (或仅 warnings)

- [ ] **Step 3: 运行现有测试确保无回归**

Run: `rtk python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(council): pass all tests and type checks"
```
