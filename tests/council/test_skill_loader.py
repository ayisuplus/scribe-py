import pytest

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


def test_load_writer_persona_from_generic_md(tmp_path):
    """测试从非SKILL.md的md文件加载（如九鹭非香.md）"""
    md_content = """---
name: jiulufeixiang
---

# 九鹭非香

## 身份卡
我是九鹭非香。

## 表达DNA
短句为主。
"""
    md_path = tmp_path / "九鹭非香.md"
    md_path.write_text(md_content, encoding="utf-8")

    persona = load_writer_persona(tmp_path)
    assert persona.identity is not None
    assert "九鹭非香" in persona.identity


def test_load_writer_persona_missing_file(tmp_path):
    """测试目录中没有md文件"""
    with pytest.raises(FileNotFoundError):
        load_writer_persona(tmp_path)
