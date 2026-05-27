# MemPalace Integration — Design Spec

**Date:** 2026-05-23
**Status:** Approved
**Scope:** Integrate MemPalace as the 4th memory layer ("detail layer") in scribe-py

## Goal

Scribe 的写作 agent 需要记住每一个细节。MemPalace 已经存储了完整的小说结构（章节摘要、场景、关键事件）。将 MemPalace 直接焊接进 scribe 的记忆系统，让 agent 写作时能自动检索相关细节，写完后自动归档。

## Architecture

### Memory Layers (after integration)

```
EpisodicStore    — 对话事件时间线
SemanticStore    — 实体/关系知识图谱
ProceduralStore  — 风格画像/技能
MemPalaceStore   — 细节层（章节摘要、场景、关键事件）← NEW
```

### Data Flow

```
写作场景：
  用户: "写第十一章：夺巢"
  → ContextAssembler 搜索 MemPalace ("夺巢" "甲龙" "林凌")
  → 注入前章关键场景摘要到 system prompt
  → AgentLoop 生成
  → 审计通过
  → 自动 mine 新章节到 MemPalace

查询场景：
  用户: "林凌之前用过什么武器？"
  → PalaceSearchTool 搜索 → 返回石矛等记录
```

### System Prompt Injection

`ContextAssembler.assemble_system_prompt()` 新增 MemPalace 部分：

```
[existing persona/style/rules/hook/episodic/semantic...]

## 相关章节记忆
以下是从记忆宫殿中检索到的与当前写作相关的章节摘要：

[MemPalace search results for keywords extracted from conversation]

---
```

Keywords extracted from: 最近 3 条对话内容 + 用户名 + session topic.

## Components

### 1. `scribe/memory/palace.py` — MemPalaceStore

```python
class MemPalaceStore:
    """MemPalace integration — 4th memory layer for detail retrieval."""

    def __init__(self, palace_path: Path | None = None):
        """
        palace_path: Path to palace directory.
        Default: ~/.mempalace/palace
        """
        ...

    async def search(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 5,
    ) -> list[PalaceHit]:
        """Search drawers by keyword. Returns matching drawer summaries."""
        ...

    async def wake_up(self) -> str:
        """Get L0+L1 wake-up context (~600-900 tokens)."""
        ...

    async def mine(
        self,
        content: str,
        wing: str,
        room: str,
        title: str,
    ) -> None:
        """Mine content into the palace as a new drawer."""
        ...

    async def status(self) -> PalaceStatus:
        """Get palace status (wings, rooms, drawer counts)."""
        ...
```

Implementation approach:
- Import `mempalace` Python package directly (not CLI subprocess)
- Use palace's Python API for search/mine/wake-up
- Async wrapper with `asyncio.to_thread()` for sync palace calls
- Configurable palace path (default `~/.mempalace/palace`)

### 2. `scribe/tools/palace_search.py` — PalaceSearchTool

```python
class PalaceSearchTool(Tool):
    """Search MemPalace for story details, scenes, character info."""

    def name(self) -> str:
        return "palace_search"

    def description(self) -> str:
        return "Search the memory palace for story details, scenes, characters, and events."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "wing": {"type": "string", "description": "Limit to a specific project"},
                "room": {"type": "string", "description": "Limit to a specific section"},
                "results": {"type": "integer", "description": "Number of results (default 5)"},
            },
            "required": ["query"],
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        ...
```

### 3. ContextAssembler Changes

```python
class ContextAssembler:
    def __init__(self, ...):
        ...
        self.palace: MemPalaceStore | None = None  # NEW

    def with_palace(self, palace: MemPalaceStore) -> ContextAssembler:  # NEW
        self.palace = palace
        return self

    async def assemble_system_prompt(self, session_id=None) -> str:
        parts = []
        # ... existing persona/style/rules/hook/episodic/semantic ...

        # NEW: MemPalace context
        if self.palace:
            keywords = self._extract_palace_keywords(parts)
            if keywords:
                hits = []
                for kw in keywords[:3]:
                    results = await self.palace.search(kw, limit=3)
                    hits.extend(results)
                if hits:
                    deduped = list({h.title: h for h in hits}.values())
                    palace_text = "\n".join(f"- {h.summary}" for h in deduped[:8])
                    parts.append(f"## 相关章节记忆\n{palace_text}")

        # ... critical instruction ...
```

### 4. AgentLoop Changes

```python
async def _run_impl(self, ...):
    # ... existing loop ...

    # After loop completes, auto-mine if writing config enabled
    if self._writing_config and self._writing_config.enabled and self._palace:
        content = response.content or ""
        if len(content) > 100:  # Only mine substantial content
            await self._palace.mine(
                content=content,
                wing=self._palace_default_wing,
                room=self._palace_default_room,
                title=f"session_{session_id}_{datetime.now().isoformat()}",
            )
```

### 5. ScribeState Changes

```python
class ScribeState:
    def __init__(self, ...):
        ...
        self._palace = MemPalaceStore()  # NEW

    def _build_agent(self) -> AgentLoop:
        agent = AgentLoop(
            llm=self._llm,
            tools=self._tools,
            episodic=self._episodic,
            semantic=self._semantic,
            procedural=self._procedural,
        )
        agent._palace = self._palace  # NEW
        ...
```

### 6. ToolRegistry Changes

In `_build_tools()`:
```python
if "palace_search" in enabled:
    from scribe.tools.palace_search import PalaceSearchTool
    registry.register(PalaceSearchTool(self._palace))
```

### 7. Config Changes

`KernelConfig` additions:
```python
palace_enabled: bool = True
palace_path: str | None = None  # default ~/.mempalace/palace
palace_auto_mine: bool = True  # auto-mine after writing
palace_default_wing: str | None = None
palace_default_room: str | None = None
```

## Dependencies

Add to `pyproject.toml`:
```
"mempalace>=3.3.0",
```

## Files Changed

| File | Change |
|------|--------|
| `scribe/memory/palace.py` | NEW — MemPalaceStore |
| `scribe/tools/palace_search.py` | NEW — PalaceSearchTool |
| `scribe/memory/assembler.py` | Add palace keyword search + prompt injection |
| `scribe/agent/loop.py` | Add auto-mine after writing |
| `scribe/api/state.py` | Init MemPalaceStore, wire into agent/assembler |
| `scribe/kernel/config.py` | Add palace config fields |
| `scribe/tools/registry.py` | Register PalaceSearchTool |
| `scribe/memory/__init__.py` | Export MemPalaceStore |
| `scribe/__init__.py` | Export MemPalaceStore |
| `pyproject.toml` | Add mempalace dependency |
| `tests/memory/test_palace.py` | NEW — tests for MemPalaceStore |
| `tests/tools/test_palace_search.py` | NEW — tests for PalaceSearchTool |

## Testing Strategy

- Mock `mempalace` package in tests (don't require real palace)
- Test MemPalaceStore.search returns correct PalaceHit objects
- Test PalaceSearchTool.execute calls store correctly
- Test ContextAssembler includes palace results in prompt
- Test AgentLoop auto-mines after writing
- Integration test: verify full flow with mock palace

## Non-Goals

- No semantic mapping between MemPalace drawers and scribe Entity/Relation (future)
- No MCP integration (future)
- No automatic compress scheduling (manual)
- No bidirectional sync (scribe → MemPalace only on mine, not on Entity changes)
