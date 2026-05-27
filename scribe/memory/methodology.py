"""
Writing methodology engine - ports InkOS + huashu rules into Scribe.

Ports scribe-memory/src/methodology.rs to Python.
Enhanced with huashu-proofreading anti-AI patterns:
- 6-category AI smell detection (套话/AI句式/书面词/结构机械/态度中立/细节缺失)
- Three-pass audit framework (内容审→风格审→细节审)
- Sentence length enforcement
"""

from __future__ import annotations

import re

from scribe.types import (
    AuditIssue,
    DensityRules,
    ParagraphRules,
    WritingAuditResult,
    WritingMethodologyConfig,
)

# ── Pre-compiled patterns ──

NOT_IS_PATTERN = re.compile(r"不是[^，。！？\n]+[，是]")

# AI sentence patterns (overused conjunctions)
PATTERN_BU_SHI_ER_SHI = re.compile(r"不是[^。！？\n]{2,20}而是")
PATTERN_BU_JIN_ER_QIE = re.compile(r"不仅[^。！？\n]{2,20}而且")
PATTERN_YI_FANG_MIAN = re.compile(r"一方面[^。！？\n]{2,30}另一方面")
PATTERN_SHOU_CI_QI_CI = re.compile(r"首先[，,].*其次[，,].*最后")

# Formal vocabulary → colloquial replacements
FORMAL_VOCAB: dict[str, str] = {
    "显著提升": "提高不少（请用具体数字）",
    "大幅改善": "改善很多（请用具体数字）",
    "充分利用": "用好",
    "进行操作": "直接用动词（点击/输入/选择）",
    "实现功能": "做到",
    "促进发展": "帮助",
    "有效提升": "提高（请量化）",
    "提供了便利": "方便了",
    "取得了显著成效": "效果不错（请给数据）",
    "在一定程度上": "（删掉，直接说）",
    "具有重要意义": "很重要",
    "发挥着重要作用": "很关键",
    "不可或缺": "少不了",
}

# Stock phrases (套话) — ban list from huashu-proofreading
STOCK_PHRASES: list[str] = [
    "在当今时代",
    "在当今",
    "在这样的大背景下",
    "在这样的背景下",
    "在这一背景下",
    "综上所述",
    "总而言之",
    "总的来说",
    "值得注意的是",
    "需要强调的是",
    "需要指出的是",
    "不难发现",
    "随着…的发展",
    "伴随着…",
    "以下几点",
    "主要体现在以下方面",
    "主要表现在以下几个方面",
    "接下来我们将进行",
    "由此可见",
    "毋庸置疑",
    "众所周知",
    "不可否认",
    "事实上",
    "从某种意义上说",
]


class WritingMethodology:
    """
    Writing methodology engine that ports InkOS rules into Scribe.

    Provides:
    - build_prompt(): Generate writing rules for system prompt
    - audit(): Check text against writing rules and return issues
    """

    @staticmethod
    def build_prompt(config: WritingMethodologyConfig) -> str:
        """
        Build the system prompt fragment with writing rules.

        Combines all seven rule sections into a single prompt.
        """
        sections = [
            WritingMethodology.core_rules(),
            WritingMethodology.density_rules(config.density_rules),
            WritingMethodology.paragraph_rules(config.paragraph_rules),
            WritingMethodology.narrative_techniques(),
            WritingMethodology.anti_ai_rules(),
            WritingMethodology.character_psychology(),
            WritingMethodology.reader_psychology(),
        ]

        return "\n\n".join(sections)

    @staticmethod
    def audit(text: str, config: WritingMethodologyConfig) -> WritingAuditResult:
        """
        Audit a text against writing methodology rules.

        Three-pass audit framework (huashu enhanced):
        Pass 1 - Content: facts, logic, completeness
        Pass 2 - Style: AI smell detection (6 categories)
        Pass 3 - Detail: sentence length, punctuation, rhythm
        """
        issues: list[AuditIssue] = []

        if config.audit_enabled:
            # Pass 2 - Style audit (AI smell)
            issues.extend(
                WritingMethodology.check_paragraph_lengths(text, config.paragraph_rules)
            )
            issues.extend(WritingMethodology.check_ai_markers(text))
            issues.extend(WritingMethodology.check_dash_usage(text))
            issues.extend(WritingMethodology.check_not_is_pattern(text))
            issues.extend(WritingMethodology.check_stock_phrases(text))
            issues.extend(WritingMethodology.check_ai_sentence_patterns(text))
            issues.extend(WritingMethodology.check_formal_vocab(text))

            # Pass 3 - Detail audit
            issues.extend(WritingMethodology.check_sentence_lengths(text))

        # Calculate score
        if not issues:
            score = 1.0
        else:
            critical = sum(1 for i in issues if i.severity == "critical")
            warning = sum(1 for i in issues if i.severity == "warning")
            score = max(0.0, 1.0 - (critical * 0.2 + warning * 0.05))

        return WritingAuditResult(
            score=score,
            issues=issues,
        )

    @staticmethod
    def core_rules() -> str:
        """Core writing rules section."""
        return """\
## 写作核心规则

1. 句式多样化：长短句交替，严禁连续使用相同句式或相同主语开头
2. 伏笔前后呼应，不留悬空线；所有埋下的伏笔都必须在后续收回
3. 人物立体化：核心标签 + 反差细节 = 活人；十全十美的人设是失败的
4. 拒绝工具人：配角必须有独立动机和反击能力
5. 角色区分度：不同角色的说话语气、发怒方式、处事模式必须有显著差异
6. 情感/动机逻辑链：任何关系的改变都必须有铺垫和事件驱动"""

    @staticmethod
    def density_rules(rules: DensityRules) -> str:
        """Content density rules section."""
        return f"""\
## 看点密集度

- **每 {rules.fun_per_chars} 字至少 1 个爽点**：小看点、有趣的梗、反套路小动作、情绪拉扯都算
- **每 {rules.hook_per_chars} 字至少 1 个钩子**：引发读者"接下来怎样"的小悬念
- **每 {rules.suspense_per_chars} 字至少 1 个完整悬念**：一组"问题—蓄力—未解"的结构
- 如果某段连续 300 字以上是环境、回忆、议论、心理独白而没有推进主线或制造看点，就是水文"""

    @staticmethod
    def paragraph_rules(rules: ParagraphRules) -> str:
        """Paragraph structure rules section."""
        return f"""\
## 段落规则

- 叙事段（非对话）**必须 ≥ {rules.min_narrative_chars} 字**——低于这个数就是碎片段落
- 目标长度：叙事段 {rules.target_min_chars}-{rules.target_max_chars} 字，允许偶尔到 150 字讲一段连贯动作链
- 短段（<{rules.min_narrative_chars} 字）只在三个场景允许：开场金句、章末钩子、爆点短段
- 一章最多 {rules.max_short_paragraphs} 个短段，不允许 {rules.max_consecutive_short} 个及以上短段并列连排"""

    @staticmethod
    def narrative_techniques() -> str:
        """Narrative technique rules section."""
        return """\
## 叙事技法

- Show, don't tell：用细节堆砌真实，用行动证明强大
- 五感代入法：场景描写中加入1-2种五感细节
- 对话驱动：优先用对话传递冲突和信息
- 信息分层植入：基础信息在行动中自然带出，关键设定结合剧情揭示
- 描写必须服务叙事：环境描写烘托氛围或暗示情节
- 80/20 断章：主剧情节写到 80%，剩 20% 留给下一章"""

    @staticmethod
    def anti_ai_rules() -> str:
        """Anti-AI writing rules section (InkOS + huashu enhanced)."""
        return """\
## 去AI味铁律

### 原始铁律
- 【铁律】叙述者永远不得替读者下结论
- 【铁律】正文中严禁出现分析报告式语言：禁止"核心动机""信息边界""利益最大化"等术语
- 【铁律】转折/惊讶标记词（仿佛、忽然、竟、竟然、猛地、猛然、不禁、宛如）全篇总数不超过每3000字1次
- 【铁律】同一体感/意象禁止连续渲染超过两轮
- 【硬性禁令】全文严禁出现"不是……而是……"句式
- 【硬性禁令】全文严禁出现破折号"——"，用逗号或句号断句

### 套话黑名单（huashu）
以下开头/过渡句一旦出现，必须删除或改写：
"在当今时代"、"在这样的大背景下"、"综上所述"、"总而言之"、"值得注意的是"、
"需要强调的是"、"不难发现"、"随着…的发展"、"伴随着…"、"以下几点"、
"主要体现在以下方面"、"由此可见"、"毋庸置疑"、"众所周知"

### AI句式检测（huashu）
- "不是…而是…"全篇不超过1次（超过即为AI模板）
- "不仅…而且…"禁止连续堆砌
- "一方面…另一方面…"禁止机械对仗
- "首先、其次、最后"禁止作为段落开头的固定模板

### 书面词替换（huashu）
写作时，以下书面词必须替换为口语/具体表达：
"显著提升"→用具体数字、"大幅改善"→用具体数字、"充分利用"→"用好"、
"进行操作"→直接动词、"实现功能"→"做到"、"促进发展"→"帮助"、
"有效提升"→"提高"+量化、"不可或缺"→"少不了"

### 句式节奏（huashu）
- 句子主干长度不超过25字，超过必须拆分
- 段落以句号断句为主，禁止用逗号串联超长句
- 每300-500字至少一个口语化表达（"说实话""我觉得""你看""其实"）

### 态度要求（huashu）
- 必须有明确立场，禁止"既有优点也有缺点"式的两头堵
- 禁止每句都加"可能""或许""在某些情况下"的hedging
- 有观点就直说，不确定的就说"我觉得"""

    @staticmethod
    def character_psychology() -> str:
        """Character psychology analysis rules section."""
        return """\
## 人物心理分析

每个重要角色在关键场景中的行为，必须经过以下六步推导：

1. **当前处境**：角色此刻面临什么局面？手上有什么牌？
2. **核心动机**：角色最想要什么？最害怕什么？
3. **信息边界**：角色知道什么？不知道什么？
4. **性格过滤**：同样的局面，这个角色的性格会怎么反应？
5. **行为选择**：基于以上四点，角色会做出什么选择？
6. **情绪外化**：用什么身体语言、表情、语气表达？"""

    @staticmethod
    def reader_psychology() -> str:
        """Reader psychology rules section."""
        return """\
## 读者心理学

- **期待管理**：在读者期待释放时，适当延迟以增强快感
- **信息落差**：让读者比角色多知道一点（制造紧张），或少知道一点（制造好奇）
- **情绪节拍**：压制→释放→更大的压制→更大的释放
- **锚定效应**：先给读者一个参照，再展示主角的表现
- **沉没成本**：每章都要给出"继续读下去的理由\""""

    @staticmethod
    def check_paragraph_lengths(text: str, rules: ParagraphRules) -> list[AuditIssue]:
        """Check for paragraph length issues."""
        issues: list[AuditIssue] = []
        paragraphs = text.split("\n\n")

        consecutive_short = 0
        short_count = 0

        for i, para in enumerate(paragraphs):
            trimmed = para.strip()
            if not trimmed:
                continue

            # Skip dialogue-heavy paragraphs (lines starting with quotes or dash)
            is_dialogue = any(
                ln.strip().startswith('"')
                or ln.strip().startswith('"')
                or ln.strip().startswith("—")
                or ln.strip().startswith("-")
                for ln in trimmed.split("\n")
            )

            char_count = len(trimmed)

            if not is_dialogue and char_count < rules.min_narrative_chars:
                short_count += 1
                consecutive_short += 1

                if consecutive_short >= rules.max_consecutive_short:
                    issues.append(
                        AuditIssue(
                            category="连续短段",
                            severity="warning",
                            location=f"段落 {i + 1}",
                            suggestion=f"连续 {consecutive_short} 个短段，合并或扩展",
                        )
                    )
            else:
                consecutive_short = 0

        if short_count > rules.max_short_paragraphs:
            issues.append(
                AuditIssue(
                    category="段落过碎",
                    severity="warning",
                    location="全文",
                    suggestion=f"短段数量 {short_count} 超过上限 {rules.max_short_paragraphs}",
                )
            )

        return issues

    @staticmethod
    def check_ai_markers(text: str) -> list[AuditIssue]:
        """Check for excessive AI marker words."""
        issues: list[AuditIssue] = []
        markers = ["仿佛", "忽然", "竟", "竟然", "猛地", "猛然", "不禁", "宛如"]
        char_count = len(text)
        threshold = max(1.0, char_count / 3000.0)

        total = sum(text.count(marker) for marker in markers)

        if total > threshold:
            issues.append(
                AuditIssue(
                    category="AI味标记词过多",
                    severity="warning",
                    location="全文",
                    suggestion=f"标记词出现 {total} 次，阈值 {threshold:.0f}",
                )
            )

        return issues

    @staticmethod
    def check_dash_usage(text: str) -> list[AuditIssue]:
        """Check for dash (——) usage."""
        issues: list[AuditIssue] = []

        if "——" in text:
            issues.append(
                AuditIssue(
                    category="破折号使用",
                    severity="info",
                    location="全文",
                    suggestion='检测到破折号"——"，建议用逗号或句号替代',
                )
            )

        return issues

    @staticmethod
    def check_not_is_pattern(text: str) -> list[AuditIssue]:
        """Check for prohibited '不是...而是...' sentence pattern."""
        issues: list[AuditIssue] = []

        if NOT_IS_PATTERN.search(text):
            issues.append(
                AuditIssue(
                    category="禁用句式",
                    severity="warning",
                    location="全文",
                    suggestion='检测到"不是...而是..."句式，改用直述句',
                )
            )

        return issues

    @staticmethod
    def check_stock_phrases(text: str) -> list[AuditIssue]:
        """Check for stock phrases (套话) — huashu ban list."""
        issues: list[AuditIssue] = []

        for phrase in STOCK_PHRASES:
            if phrase in text:
                issues.append(
                    AuditIssue(
                        category="套话",
                        severity="warning",
                        location="全文",
                        suggestion=f'检测到套话"{phrase}"，删除或改写为直切主题的表达',
                    )
                )

        return issues

    @staticmethod
    def check_ai_sentence_patterns(text: str) -> list[AuditIssue]:
        """Check for AI sentence patterns (AI句式) — huashu detection."""
        issues: list[AuditIssue] = []

        # "不是...而是..." count (allow 1, flag 2+)
        bu_shi_matches = PATTERN_BU_SHI_ER_SHI.findall(text)
        if len(bu_shi_matches) >= 2:
            issues.append(
                AuditIssue(
                    category="AI句式",
                    severity="warning",
                    location="全文",
                    suggestion=f'"不是…而是…"出现{len(bu_shi_matches)}次，AI模板特征，最多保留1次',
                )
            )

        # "不仅...而且..." stacked
        bu_jin_matches = PATTERN_BU_JIN_ER_QIE.findall(text)
        if len(bu_jin_matches) >= 2:
            issues.append(
                AuditIssue(
                    category="AI句式",
                    severity="warning",
                    location="全文",
                    suggestion=f'"不仅…而且…"出现{len(bu_jin_matches)}次，禁止堆砌，拆成短句',
                )
            )

        # "一方面...另一方面..."
        yi_fang_matches = PATTERN_YI_FANG_MIAN.findall(text)
        if yi_fang_matches:
            issues.append(
                AuditIssue(
                    category="AI句式",
                    severity="warning",
                    location="全文",
                    suggestion='检测到"一方面…另一方面…"机械对仗，改用自然叙述',
                )
            )

        # "首先、其次、最后" template
        if PATTERN_SHOU_CI_QI_CI.search(text):
            issues.append(
                AuditIssue(
                    category="AI句式",
                    severity="warning",
                    location="全文",
                    suggestion='检测到"首先、其次、最后"模板化枚举，改用自然过渡',
                )
            )

        return issues

    @staticmethod
    def check_formal_vocab(text: str) -> list[AuditIssue]:
        """Check for formal/written vocabulary (书面词) — huashu replacements."""
        issues: list[AuditIssue] = []

        for formal, replacement in FORMAL_VOCAB.items():
            if formal in text:
                issues.append(
                    AuditIssue(
                        category="书面词",
                        severity="info",
                        location="全文",
                        suggestion=f'"{formal}"→{replacement}',
                    )
                )

        return issues

    @staticmethod
    def check_sentence_lengths(text: str, max_chars: int = 25) -> list[AuditIssue]:
        """Check for overly long sentences (huashu: max 25 chars per main clause)."""
        issues: list[AuditIssue] = []

        # Split by sentence-ending punctuation
        sentences = re.split(r"[。！？\n]", text)

        long_count = 0
        for i, sent in enumerate(sentences):
            trimmed = sent.strip()
            if not trimmed:
                continue
            # Count chars excluding punctuation and spaces
            content = re.sub(r'[，、；：""' "（） ]", "", trimmed)
            if len(content) > max_chars:
                long_count += 1

        if long_count > 0:
            issues.append(
                AuditIssue(
                    category="句子过长",
                    severity="warning" if long_count >= 3 else "info",
                    location="全文",
                    suggestion=f"{long_count}个句子主干超过{max_chars}字，拆分成短句",
                )
            )

        return issues
