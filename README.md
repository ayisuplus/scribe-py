# Scribe — AI 写作助手

命令行 AI 写作助手，支持 DeepSeek / OpenAI / Anthropic。理解你的写作风格，越用越像你。

融合三大开源项目精华：
- **OpenHanako** — 人格模板系统、意识流模式、文学级反AI腔规则
- **InkOS** — 25+ 写作方法论规则、看点密度控制、伏笔账本、审计修订循环
- **ACPX** — Agent Client Protocol (ACP) 协议支持

## 快速开始

### 1. 安装

```bash
pip install -e .
```

或从源码安装：

```bash
git clone https://github.com/example/scribe-py.git
cd scribe-py
pip install -e .
```

### 2. 配置 API Key

设置环境变量：

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export DEEPSEEK_API_KEY=sk-...
```

或在运行时使用 `/apikey` 命令设置（交互模式中可用）。

### 3. 运行

```bash
# 交互模式（默认）
scribe

# 单次提问
scribe -p "你好"

# 列出历史会话
scribe --list-sessions

# MCP 服务器模式（供 Claude Code 等工具集成）
scribe --mcp
```

## 交互模式命令

| 命令 | 说明 |
|------|------|
| 直接输入文字 | 发送给 AI |
| `/help` | 显示帮助 |
| `/status` | 当前配置和会话 |
| `/config` | 交互式配置向导 |
| `/apikey` | 设置 API key |
| `/provider openai\|deepseek\|anthropic` | 切换提供商 |
| `/model gpt-4o` | 切换模型 |
| `/sessions` | 历史会话列表 |
| `/new` | 新建会话 |
| `/switch <id>` | 切换到指定会话 |
| `/clear` | 清空当前会话 |
| `/exit` | 退出 |

## 特性

### 人格模板系统

在 `~/.scribe/persona/` 下放置 markdown 文件自定义 Scribe 的人格：

```
~/.scribe/persona/
  identity.md    # 基础身份（必填）
  ishiki.md      # 说话风格、反AI腔规则
  yuan.md        # 意识流模式（MOOD/REFLECT，可选）
```

`identity.md` 中可用 `{{user_name}}` 占位符，运行时替换为用户名。

### 写作方法论

启用后 Scribe 会自动注入 25+ 写作规则（看点密度、段落形态、去AI味铁律、角色心理六步推导、读者心理学），并在生成文本后自动审计修订。

### 伏笔账本

通过 `HookLedgerManager` 管理伏笔生命周期：`planted → pressured → resolved`。
数据存储在 `~/.scribe/data/books/{id}/hooks.json`。

### MCP 服务器

`--mcp` 模式启动 JSON-RPC over stdin/stdout 服务器，支持：

| 工具 | 说明 |
|------|------|
| `scribe_write` | 生成文本（应用人格/写作规则） |
| `scribe_audit` | 审计文本质量 |
| `scribe_session_new` | 创建新会话 |

## 项目结构

```
scribe/
├── scribe/types.py         # 核心类型定义
├── scribe/kernel/          # 内核（配置/会话/事件总线）
├── scribe/memory/          # 三层记忆 + 人格加载 + 写作方法论 + 伏笔账本
├── scribe/llm/             # LLM 驱动（DeepSeek/OpenAI/Anthropic）
├── scribe/tools/           # 工具集（文件读写/搜索/网页抓取）
├── scribe/agent/           # Agent 循环 + 审计修订循环
├── scribe/api/             # 桥接层（ScribeState API）
└── scribe/cli/             # 命令行入口 + MCP 服务器
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest -v

# 运行集成冒烟测试
python tests/smoke_test.py
python tests/test_mcp_smoke.py
```