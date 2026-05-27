"""
Writer Distiller — Nuwa-style skill extraction for writers.

Based on the nuwa-skill methodology (https://github.com/alchaincyf/nuwa-skill).

The distillation process:
1. Phase 0: Confirm target (real author name + direction)
2. Phase 1: Multi-source research (parallel agents)
3. Phase 2: Framework extraction (mental models + expression DNA)
4. Phase 3: Skill construction (identity.md + ishiki.md)
5. Phase 4: Quality validation
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.council.registry import Writer, WriterGenre
from scribe.types import ChatRequest, Message, Role

if TYPE_CHECKING:
    from scribe.llm.base import LlmDriver

logger = logging.getLogger(__name__)


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    # Remove special characters, keep Chinese and alphanumeric
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"[_\s]+", "-", slug)
    slug = slug.strip("-").lower()
    return slug


class WriterDistiller:
    """
    Distill a real author's writing style into a Writer persona.

    Inspired by nuwa-skill's methodology:
    - Multi-source research (works, interviews, criticism)
    - Mental model extraction (how they think)
    - Expression DNA extraction (how they write)
    - Quality validation against known statements
    """

    def __init__(self, llm: LlmDriver) -> None:
        self._llm = llm

    async def distill(
        self,
        real_name: str,
        genre: str = "fiction",
        direction: str = "all",
        sources: list[str] | None = None,
    ) -> Writer:
        """
        Distill a writer from research.

        Args:
            real_name: The real author's name
            genre: Primary genre (fiction, essay, etc.)
            direction: Focus direction (all, style, structure, voice)
            sources: Optional list of source URLs/texts to analyze

        Returns:
            A distilled Writer object
        """
        writer_id = slugify(real_name)
        logger.info(f"Starting distillation for: {real_name} (id: {writer_id})")

        # Phase 0: Create work directory
        work_dir = Path.home() / ".scribe" / "writers" / "writers" / writer_id
        work_dir.mkdir(parents=True, exist_ok=True)
        research_dir = work_dir / "research"
        research_dir.mkdir(exist_ok=True)

        # Phase 1: Research
        research_results = await self._phase1_research(
            real_name, work_dir, sources
        )

        # Phase 2: Extract frameworks
        frameworks = await self._phase2_extract(
            real_name, research_results, direction
        )

        # Phase 3: Build persona
        writer = await self._phase3_build(
            writer_id=writer_id,
            real_name=real_name,
            genre=genre,
            frameworks=frameworks,
            work_dir=work_dir,
        )

        logger.info(f"Distillation complete: {writer.name}")
        return writer

    async def _phase1_research(
        self,
        real_name: str,
        work_dir: Path,
        sources: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Phase 1: Multi-source research.

        Research dimensions (inspired by nuwa-skill's 6 agents):
        1. Works - books, major works, recurring themes
        2. Style - writing patterns, sentence structures, vocabulary
        3. Philosophy - worldview, values, themes
        4. Biography - key life events, influences
        5. Criticism - how others analyze this author
        6. Interviews - direct statements about craft

        Returns:
            Dict mapping dimension to research text
        """
        research_prompt = f"""你正在研究作家 {real_name} 的写作风格和思维方式。

请从以下6个维度进行深度调研，每个维度至少找到3-5个关键发现：

1. **作品分析** - 代表作、核心主题、叙事风格
2. **写作技法** - 句子结构、用词偏好、修辞手法
3. **思想哲学** - 世界观、价值观、创作理念
4. **人生经历** - 关键事件、成长背景、文学影响
5. **他人评价** - 批评家观点、同行评价
6. **访谈自述** - 作者本人的创作谈

对于每位作家，重点关注：
- 他们如何处理故事/人物/主题
- 他们对写作本身的看法（如果谈过）
- 他们的标志性风格特征
- 他们与其他作家的区别

请输出结构化的调研报告，标注每个发现的信息来源。

输出格式：
```
## 维度1: [维度名称]
[发现1] - [来源]
[发现2] - [来源]
...

## 维度2: [维度名称]
...
```
"""

        try:
            req = ChatRequest(
                model="",  # Use default
                messages=[Message(role=Role.USER, content=research_prompt)],
            )
            response = await self._llm.chat(req)

            research_text = response.content if response.content else ""

            # Save to research file
            research_file = work_dir / "research" / "01-initial-research.md"
            research_file.write_text(
                f"# {real_name} 调研报告\n"
                f"调研时间: {datetime.now(UTC).isoformat()}\n\n"
                f"{research_text}",
                encoding="utf-8",
            )

            # Return structured results
            return {
                "research": research_text,
                "sources": sources or [],
            }

        except Exception as e:
            logger.warning(f"Research phase failed: {e}")
            return {"research": "", "sources": sources or []}

    async def _phase2_extract(
        self,
        real_name: str,
        research_results: dict[str, str],
        direction: str,
    ) -> dict:
        """
        Phase 2: Extract mental models and expression DNA.

        From research results, extract:
        - 3-5 core mental models (how this writer thinks)
        - Expression DNA (how they write)
        - Key themes and concerns
        """
        research_text = research_results.get("research", "")

        if not research_text:
            return self._default_frameworks(real_name)

        extract_prompt = f"""基于以下关于 {real_name} 的调研材料，请提取：

## 1. 核心思维模型 (3-5个)

每个思维模型包含：
- **名称**: 一句话概括
- **描述**: 这个模型的核心内容
- **应用**: 在什么写作场景中使用这个模型

## 2. 表达DNA (写作风格特征)

- **句式偏好**: 长句/短句、陈述/疑问
- **词汇特征**: 高频词、专属术语
- **节奏感**: 转折方式、段落结构
- **声音特征**: 第一人称/第三人称、叙事距离

## 3. 核心主题

这位作家最常处理的主题是什么？有什么独特的关注点？

## 4. 说话风格

如果这位作家在对话中谈论写作，他们会怎么说？

---

调研材料:
{research_text[:8000]}  # Limit to avoid token overflow

输出格式: JSON
{{
  "mental_models": [
    {{"name": "...", "description": "...", "application": "..."}}
  ],
  "expression_dna": {{
    "sentence_patterns": "...",
    "vocabulary": "...",
    "rhythm": "...",
    "voice": "..."
  }},
  "themes": ["..."],
  "speaking_style": "..."
}}
"""

        try:
            req = ChatRequest(
                model="",  # Use default
                messages=[Message(role=Role.USER, content=extract_prompt)],
            )
            response = await self._llm.chat(req)

            content = response.content if response.content else "{}"
            # Try to extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                frameworks = json_module.loads(json_match.group())
            else:
                frameworks = self._default_frameworks(real_name)

            return frameworks

        except Exception as e:
            logger.warning(f"Extraction phase failed: {e}")
            return self._default_frameworks(real_name)

    async def _phase3_build(
        self,
        writer_id: str,
        real_name: str,
        genre: str,
        frameworks: dict,
        work_dir: Path,
    ) -> Writer:
        """
        Phase 3: Build the Writer persona.

        Creates:
        - identity.md: Core identity and thinking patterns
        - ishiki.md: Speaking/writing style rules
        """

        mental_models = frameworks.get("mental_models", [])
        expression_dna = frameworks.get("expression_dna", {})
        themes = frameworks.get("themes", [])
        speaking_style = frameworks.get("speaking_style", "")

        # Build identity.md
        identity_parts = [f"# {real_name}\n\n"]
        identity_parts.append(
            f"你是作家 {real_name} 的写作风格化身。你了解这位作家的思维方式、创作理念和表达方式。\n\n"
        )

        # Add mental models
        if mental_models:
            identity_parts.append("## 思维方式\n")
            for model in mental_models:
                name = model.get("name", "")
                desc = model.get("description", "")
                app = model.get("application", "")
                identity_parts.append(f"### {name}\n")
                identity_parts.append(f"{desc}\n")
                if app:
                    identity_parts.append(f"**应用场景**: {app}\n")
                identity_parts.append("\n")

        # Add themes
        if themes:
            identity_parts.append("## 核心主题\n")
            for theme in themes:
                identity_parts.append(f"- {theme}\n")
            identity_parts.append("\n")

        identity = "".join(identity_parts)

        # Build ishiki.md
        ishiki_parts = ["# 说话与写作风格\n\n"]

        if expression_dna:
            patterns = expression_dna.get("sentence_patterns", "")
            vocabulary = expression_dna.get("vocabulary", "")
            rhythm = expression_dna.get("rhythm", "")
            voice = expression_dna.get("voice", "")

            if patterns:
                ishiki_parts.append(f"## 句式偏好\n{patterns}\n\n")
            if vocabulary:
                ishiki_parts.append(f"## 词汇特征\n{vocabulary}\n\n")
            if rhythm:
                ishiki_parts.append(f"## 节奏感\n{rhythm}\n\n")
            if voice:
                ishiki_parts.append(f"## 声音\n{voice}\n\n")

        if speaking_style:
            ishiki_parts.append(f"## 谈论写作时\n{speaking_style}\n\n")

        # Default style rules
        ishiki_parts.append("## 基本规则\n")
        ishiki_parts.append(
            "- 不要说「好的」「我明白了」等客套话，直接回应\n"
            "- 用第一人称，像这位作家本人在说话\n"
            "- 关于写作的问题，用这位作家的视角和语言回答\n"
            "- 不要跳出角色做meta分析\n"
        )

        ishiki = "".join(ishiki_parts)

        # Create Writer object
        now = datetime.now(UTC).isoformat()
        writer = Writer(
            id=writer_id,
            name=real_name,
            real_name=real_name,
            genre=genre,
            description=f"{real_name} 的写作风格",
            identity=identity,
            ishiki=ishiki,
            mental_models=[m.get("name", "") for m in mental_models],
            expression_dna=[expression_dna.get("sentence_patterns", "")],
            source_count=1,  # TODO: count actual sources
            distilled_at=now,
            updated_at=now,
        )

        # Save persona files
        (work_dir / "identity.md").write_text(identity, encoding="utf-8")
        (work_dir / "ishiki.md").write_text(ishiki, encoding="utf-8")
        writer_json_path = work_dir / "writer.json"
        writer_json_path.write_text(
            json.dumps(writer.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return writer

    def _default_frameworks(self, real_name: str) -> dict:
        """Return default frameworks when extraction fails."""
        return {
            "mental_models": [
                {
                    "name": "叙事视角",
                    "description": f"从特定视角观察世界的习惯",
                    "application": "处理人物和场景时考虑视角选择",
                }
            ],
            "expression_dna": {
                "sentence_patterns": "使用简洁有力的句子",
                "vocabulary": "精准的用词",
                "rhythm": "节奏感强",
                "voice": "第一人称叙事",
            },
            "themes": ["人生", "存在", "关系"],
            "speaking_style": f"谈论写作时注重实践和直觉",
        }