# Memory System Simplification — 记忆系统简化

> **Goal:** 简化记忆系统，删除辩论系统，让写作风格完全由作家人格主导

**Architecture:** 记忆系统只保留 EpisodicStore（进度保存）+ PersonaLoader（人格）+ WritingMethodology（方法论）。辩论系统（council/）全删。语义/伏笔/记忆宫殿等复杂度全部移除。

**Tech Stack:** Python, JSON file storage

---

## 删除的模块

### council/ — 全删

| 文件 | 删除原因 |
|---|---|
| `council.py` | 主编排器，辩论流程 |
| `writer_agent.py` | 作家代理，含死代码 `load_writer_persona` |
| `editor.py` | 主编裁决 |
| `debate_state.py` | 辩论状态 |
| `router.py` | 路由 |
| `wizard.py` | 写作向导 |
| `__init__.py` | 清空导出 |

### memory/ — 删除 6 个模块

| 文件 | 删除原因 |
|---|---|
| `semantic.py` | 实体/关系知识图谱，未被充分使用 |
| `procedural.py` | 风格档案，风格由人格主导 |
| `hook_ledger.py` | 伏笔追踪，过度工程化 |
| `palace.py` | 记忆宫殿，复杂度高 |
| `extractor.py` | 实体抽取，依赖 semantic |
| `assembler.py` | 上下文组装器，逻辑简单可内联 |

### types.py — 删除相关类型

```
删除：
- Entity, Relation  (semantic)
- StyleProfile, PunctuationStyle, Tone, EllipsisStyle, QuoteStyle  (procedural)
- HookEntry, HookLedger, HookStatus  (hook_ledger)
- PalaceHit, PalaceStatus  (palace)
- WriterDebateState, WriterOpinion  (council)
- ConsciousnessMode, ConsciousnessBlock, ConsciousnessSection  (persona 简化)
- AuditIssue, WritingAuditResult, HookHealthIssue  (保留 DensityRules/ParagraphRules)
```

### tests/ — 删除相关测试

```
删除 tests/council/ 全部
保留 tests/memory/test_semantic.py, test_palace.py? → 删除
保留 tests/test_persona.py? → 删除（测试 PersonaLoader 简化版）
保留 tests/test_hook_ledger.py? → 删除
```

---

## 保留的模块

### memory/episodic.py
对话事件持久化。保持原样。

### memory/persona.py
人格加载器。**简化**：移除 `yuan.md` 支持、`consciousness_mode`、Yuan 相关逻辑。PersonaConfig 只保留 `identity`、`ishiki`、`name`。

### memory/methodology.py
写作方法论。保持原样（anti-AI 规则、去套话等）。

### types.py — 保留的核心类型

```python
# Memory
@dataclass class MemoryEvent: ...
@dataclass class SessionInfo: ...

# Persona (简化)
@dataclass class PersonaConfig:
    identity: str
    ishiki: str
    name: str | None = None

# Writing Methodology (保留)
@dataclass class WritingMethodologyConfig: ...
@dataclass class DensityRules: ...
@dataclass class ParagraphRules: ...

# Core
type SessionId = str
class Role: SYSTEM, USER, ASSISTANT, TOOL
@dataclass class Message: ...
@dataclass class ChatRequest: ...
@dataclass class ChatResponse: ...
@dataclass class ToolCall: ...
@dataclass class ToolResult: ...
```

### agent/loop.py
**简化 `_assemble_system_prompt`**：

```python
async def _assemble_system_prompt(self) -> str:
    parts = []

    # 1. 人格（身份 + 说话风格）
    if self._persona:
        parts.append(self._persona.identity)
        if self._persona.ishiki:
            parts.append(self._persona.ishiki)

    # 2. 写作方法论（全局约束）
    if self._writing_config and self._writing_config.enabled:
        parts.append(WritingMethodology.build_prompt(self._writing_config))

    return "\n\n".join(parts) if parts else "You are a helpful assistant."
```

移除：
- `_palace`、`_semantic`、`_procedural` 字段
- `with_palace()` 方法
- `with_hook_ledger()` 方法
- MemPalace 自动挖掘逻辑
- Semantic entity 注入逻辑

### api/state.py
移除 4 个 memory store 初始化（semantic, procedural, palace, hook_ledger），只保留 episodic。

---

## 文件变更清单

### 删除

```
scribe/council/           (整个目录)
scribe/memory/semantic.py
scribe/memory/procedural.py
scribe/memory/hook_ledger.py
scribe/memory/palace.py
scribe/memory/extractor.py
scribe/memory/assembler.py
scribe/__init__.py         (删除相关导出)
tests/council/             (整个目录)
tests/memory/test_semantic.py
tests/memory/test_palace.py
tests/test_hook_ledger.py
tests/test_persona.py
tests/memory/test_assembler.py
```

### 修改

```
scribe/memory/persona.py   — 简化 PersonaLoader，移除 yuan/consciousness
scribe/memory/__init__.py  — 更新导出
scribe/types.py            — 删除多余类型
scribe/agent/loop.py       — 简化 _assemble_system_prompt
scribe/api/state.py        — 移除多余 memory store 初始化
```

### 清理 tools/

```
scribe/tools/memory_tool.py  — 依赖 semantic/procedural，删除
scribe/tools/palace_search.py — 依赖 palace，删除
scribe/tools/registry.py     — 移除相关 tool 注册
```

---

## Spec Self-Review

- [x] 无 placeholder/TODO
- [x] 无矛盾（所有删除项都有明确原因）
- [x] 范围清晰（只涉及记忆系统简化）
- [x] 文件边界清晰（每项删除/修改都有具体文件路径）
