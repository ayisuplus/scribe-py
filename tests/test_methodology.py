"""
Tests for scribe.memory.methodology module.

Critical tests for Chinese writing rules.
"""

import pytest

from scribe.types import (
    WritingMethodologyConfig,
    DensityRules,
    ParagraphRules,
    WritingAuditResult,
    AuditIssue,
)

from scribe.memory.methodology import WritingMethodology


class TestBuildPrompt:
    """Test build_prompt generates all rule sections."""

    def test_build_prompt_contains_all_sections(self):
        """Test that build_prompt includes all 7 rule sections."""
        config = WritingMethodologyConfig()
        prompt = WritingMethodology.build_prompt(config)
        
        # Check for all required sections
        assert "写作核心规则" in prompt
        assert "看点密集度" in prompt
        assert "段落规则" in prompt
        assert "叙事技法" in prompt
        assert "去AI味铁律" in prompt
        assert "人物心理分析" in prompt
        assert "读者心理学" in prompt

    def test_build_prompt_density_rules_with_custom_values(self):
        """Test density rules use custom config values."""
        config = WritingMethodologyConfig(
            density_rules=DensityRules(
                fun_per_chars=400,
                hook_per_chars=600,
                suspense_per_chars=2000,
            )
        )
        prompt = WritingMethodology.build_prompt(config)
        
        assert "每 400 字至少 1 个爽点" in prompt
        assert "每 600 字至少 1 个钩子" in prompt
        assert "每 2000 字至少 1 个完整悬念" in prompt

    def test_build_prompt_paragraph_rules_with_custom_values(self):
        """Test paragraph rules use custom config values."""
        config = WritingMethodologyConfig(
            paragraph_rules=ParagraphRules(
                min_narrative_chars=50,
                target_min_chars=50,
                target_max_chars=150,
                max_short_paragraphs=3,
                max_consecutive_short=2,
            )
        )
        prompt = WritingMethodology.build_prompt(config)
        
        assert "必须 ≥ 50 字" in prompt
        assert "50-150 字" in prompt
        assert "最多 3 个短段" in prompt
        assert "不允许 2 个及以上" in prompt


class TestAudit:
    """Test audit functionality."""

    def test_audit_clean_text(self):
        """Test audit on clean text passes."""
        config = WritingMethodologyConfig()
        text = "这是一段正常的文字，没有AI味标记词，也没有破折号。段落长度足够，不会被判定为短段。这是一个合格的叙事段落，包含了足够的信息量和细节描写。"
        
        result = WritingMethodology.audit(text, config)
        
        assert result.score > 0.9
        assert len(result.issues) == 0

    def test_audit_detects_dash(self):
        """Test audit detects dash usage (——)."""
        config = WritingMethodologyConfig()
        text = "他走了——然后停下来。"
        
        result = WritingMethodology.audit(text, config)
        
        assert any(i.category == "破折号使用" for i in result.issues)

    def test_audit_detects_ai_markers(self):
        """Test audit detects AI marker words."""
        config = WritingMethodologyConfig()
        text = "他忽然站起来。仿佛明白了什么。竟然笑了。猛地拍桌。不禁感叹。宛如重生。"
        
        result = WritingMethodology.audit(text, config)
        
        assert any(i.category == "AI味标记词过多" for i in result.issues)

    def test_audit_detects_not_is_pattern(self):
        """Test audit detects '不是...而是...' pattern."""
        config = WritingMethodologyConfig()
        text = "这不是坏事，而是命运的安排。"
        
        result = WritingMethodology.audit(text, config)
        
        assert any(i.category == "禁用句式" for i in result.issues)

    def test_audit_score_calculation(self):
        """Test audit score calculation formula."""
        config = WritingMethodologyConfig()
        
        # Clean text should have score 1.0
        clean_text = "这是一段足够长的叙事段落，包含足够的细节和内容。"
        result = WritingMethodology.audit(clean_text, config)
        assert result.score == 1.0

    def test_audit_short_paragraphs(self):
        """Test audit detects short paragraph issues."""
        config = WritingMethodologyConfig(
            paragraph_rules=ParagraphRules(
                min_narrative_chars=40,
                max_short_paragraphs=5,
                max_consecutive_short=3,
            )
        )
        # Multiple consecutive short paragraphs
        text = "短。\n\n很短。\n\n再短。\n\n又是短。"
        
        result = WritingMethodology.audit(text, config)
        
        # Should have issues about consecutive short paragraphs
        categories = [i.category for i in result.issues]
        assert "连续短段" in categories or "段落过碎" in categories

    def test_audit_multiple_issues(self):
        """Test audit with multiple issues."""
        config = WritingMethodologyConfig()
        text = "他忽然走了——然后停下来。这不是坏事，而是命运的安排。"
        
        result = WritingMethodology.audit(text, config)
        
        # Should detect at least dash and not-is pattern
        categories = {i.category for i in result.issues}
        assert "破折号使用" in categories
        assert "禁用句式" in categories

        # Score should be lower with multiple issues
        assert result.score < 1.0


class TestCoreRules:
    """Test individual rule sections."""

    def test_core_rules_content(self):
        """Test core_rules has correct content."""
        rules = WritingMethodology.core_rules()
        
        assert "句式多样化" in rules
        assert "伏笔前后呼应" in rules
        assert "人物立体化" in rules
        assert "拒绝工具人" in rules
        assert "角色区分度" in rules
        assert "情感/动机逻辑链" in rules

    def test_anti_ai_rules_content(self):
        """Test anti_ai_rules has correct content."""
        rules = WritingMethodology.anti_ai_rules()
        
        assert "叙述者永远不得替读者下结论" in rules
        assert "核心动机" in rules  # Prohibited term
        assert "仿佛" in rules  # Marker words
        assert "不是……而是……" in rules  # Prohibited pattern
        assert "破折号" in rules  # Prohibited dash


class TestNarrativeTechniques:
    """Test narrative techniques section."""

    def test_narrative_techniques_content(self):
        """Test narrative_techniques has correct content."""
        techniques = WritingMethodology.narrative_techniques()
        
        assert "Show, don't tell" in techniques
        assert "五感代入法" in techniques
        assert "对话驱动" in techniques
        assert "信息分层植入" in techniques
        assert "80/20 断章" in techniques


class TestCharacterPsychology:
    """Test character psychology section."""

    def test_character_psychology_content(self):
        """Test character_psychology has correct content."""
        psych = WritingMethodology.character_psychology()
        
        assert "当前处境" in psych
        assert "核心动机" in psych
        assert "信息边界" in psych
        assert "性格过滤" in psych
        assert "行为选择" in psych
        assert "情绪外化" in psych


class TestReaderPsychology:
    """Test reader psychology section."""

    def test_reader_psychology_content(self):
        """Test reader_psychology has correct content."""
        psych = WritingMethodology.reader_psychology()
        
        assert "期待管理" in psych
        assert "信息落差" in psych
        assert "情绪节拍" in psych
        assert "锚定效应" in psych
        assert "沉没成本" in psych


class TestHuashuAntiAI:
    """Test huashu-enhanced anti-AI audit methods."""

    def test_stock_phrases_detected(self):
        """Test stock phrase detection."""
        text = "在当今时代，AI技术飞速发展。综上所述，我们需要学习。"
        issues = WritingMethodology.check_stock_phrases(text)
        categories = [i.category for i in issues]
        assert "套话" in categories
        assert len(issues) >= 2

    def test_stock_phrases_clean(self):
        """Test clean text has no stock phrase issues."""
        text = "Claude Code出了。我用了两周，比Cursor好用。"
        issues = WritingMethodology.check_stock_phrases(text)
        assert len(issues) == 0

    def test_ai_sentence_patterns_bu_shi(self):
        """Test '不是...而是...' pattern count."""
        # 2 occurrences should be flagged
        text = "这不是问题，而是机会。那不是错误，而是选择。"
        issues = WritingMethodology.check_ai_sentence_patterns(text)
        assert any("不是…而是…" in i.suggestion for i in issues)

    def test_ai_sentence_patterns_bu_jin(self):
        """Test '不仅...而且...' stacked detection."""
        text = "这不仅好，而且便宜。那不仅快，而且稳定。"
        issues = WritingMethodology.check_ai_sentence_patterns(text)
        assert any("不仅…而且…" in i.suggestion for i in issues)

    def test_ai_sentence_patterns_yi_fang_mian(self):
        """Test '一方面...另一方面...' detection."""
        text = "一方面成本在涨，另一方面收入在降。"
        issues = WritingMethodology.check_ai_sentence_patterns(text)
        assert any("一方面…另一方面…" in i.suggestion for i in issues)

    def test_ai_sentence_patterns_shou_ci(self):
        """Test '首先、其次、最后' template detection."""
        text = "首先，我们需要准备。其次，开始执行。最后，验收结果。"
        issues = WritingMethodology.check_ai_sentence_patterns(text)
        assert any("首先、其次、最后" in i.suggestion for i in issues)

    def test_formal_vocab_detected(self):
        """Test formal vocabulary detection."""
        text = "这个工具可以显著提升开发效率，充分利用系统资源。"
        issues = WritingMethodology.check_formal_vocab(text)
        assert len(issues) >= 2
        assert all(i.category == "书面词" for i in issues)

    def test_formal_vocab_clean(self):
        """Test colloquial text has no formal vocab issues."""
        text = "用好这个工具，开发速度能快不少。"
        issues = WritingMethodology.check_formal_vocab(text)
        assert len(issues) == 0

    def test_sentence_lengths_long(self):
        """Test long sentence detection."""
        # 25+ char content sentence
        text = "在使用这个工具进行开发的过程中我们发现它的性能表现确实非常出色令人印象深刻。"
        issues = WritingMethodology.check_sentence_lengths(text)
        assert any(i.category == "句子过长" for i in issues)

    def test_sentence_lengths_short(self):
        """Test short sentences pass."""
        text = "这个工具很好用。速度很快。"
        issues = WritingMethodology.check_sentence_lengths(text)
        assert len(issues) == 0

    def test_audit_includes_huashu_checks(self):
        """Test that full audit includes huashu checks."""
        config = WritingMethodologyConfig()
        text = "在当今时代，AI技术显著提升。综上所述，我们需要充分利用这些工具。"
        result = WritingMethodology.audit(text, config)
        
        categories = {i.category for i in result.issues}
        assert "套话" in categories
        assert "书面词" in categories

    def test_anti_ai_rules_includes_huashu(self):
        """Test that anti_ai_rules prompt includes huashu sections."""
        rules = WritingMethodology.anti_ai_rules()
        assert "套话黑名单" in rules
        assert "AI句式检测" in rules
        assert "书面词替换" in rules
        assert "句式节奏" in rules
        assert "态度要求" in rules
