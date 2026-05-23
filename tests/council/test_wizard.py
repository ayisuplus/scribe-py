import pytest
from scribe.council.wizard import ThemeSummary, WritingScope, ScopeParser, ThemeInterviewer


def test_theme_summary_from_answers():
    answers = {
        "genre": "仙侠",
        "emotion": "虐心",
        "protagonist": "魔尊",
        "desire": "自由",
        "conflict": "人与命运",
        "setting": "三界",
        "effect": "让读者哭",
        "scene": "大战后独坐山巅",
    }
    theme = ThemeSummary.from_answers(answers)
    assert theme.genre == "仙侠"
    assert theme.emotion == "虐心"
    assert theme.scene == "大战后独坐山巅"


def test_theme_summary_summary_property():
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    summary = theme.summary
    assert "仙侠" in summary
    assert "魔尊" in summary
    assert "自由" in summary


def test_theme_summary_missing_optional():
    answers = {
        "genre": "都市", "emotion": "温暖", "protagonist": "白领",
        "desire": "成功", "conflict": "人与人", "setting": "上海",
        "effect": "让读者思考",
    }
    theme = ThemeSummary.from_answers(answers)
    assert theme.scene is None


def test_writing_scope_outline():
    scope = WritingScope(mode="outline", target=None, description="生成大纲")
    assert scope.mode == "outline"
    assert scope.target is None


def test_writing_scope_chapter():
    scope = WritingScope(mode="chapter", target="第三章", description="生成第三章")
    assert scope.mode == "chapter"
    assert scope.target == "第三章"


def test_scope_parser_outline():
    parser = ScopeParser()
    scope = parser.parse("写大纲")
    assert scope.mode == "outline"
    assert scope.target is None


def test_scope_parser_full():
    parser = ScopeParser()
    scope = parser.parse("整本书")
    assert scope.mode == "full"


def test_scope_parser_chapter_cn():
    parser = ScopeParser()
    scope = parser.parse("第3章")
    assert scope.mode == "chapter"
    assert scope.target == "第3章"


def test_scope_parser_chapter_cn_num():
    parser = ScopeParser()
    scope = parser.parse("第三章")
    assert scope.mode == "chapter"
    assert scope.target == "第三章"


def test_scope_parser_volume():
    parser = ScopeParser()
    scope = parser.parse("卷二")
    assert scope.mode == "volume"
    assert scope.target == "卷二"


def test_scope_parser_range():
    parser = ScopeParser()
    scope = parser.parse("从第3章到第7章")
    assert scope.mode == "chapter"
    assert "第3章" in scope.target
    assert "第7章" in scope.target


def test_scope_parser_default():
    parser = ScopeParser()
    scope = parser.parse("随便写写")
    assert scope.mode == "outline"


def test_theme_interviewer_questions():
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    assert len(interviewer.QUESTIONS) == 8
    assert interviewer.QUESTIONS[0][0] == "genre"
    assert interviewer.QUESTIONS[7][0] == "scene"


def test_theme_interviewer_ask_choice():
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value='1'):
        result = interviewer._ask_choice("测试问题?", ["选项A", "选项B"])
    assert result == "选项A"


def test_theme_interviewer_ask_text():
    from scribe.council.wizard import ThemeInterviewer
    interviewer = ThemeInterviewer()
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value='测试回答'):
        result = interviewer._ask_text("测试问题?")
    assert result == "测试回答"


def test_theme_summary_confirm_accept():
    from scribe.council.wizard import ThemeInterviewer
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    interviewer = ThemeInterviewer()
    import unittest.mock
    with unittest.mock.patch('builtins.input', return_value=''):
        result = theme.confirm(interviewer)
    assert result is theme


def test_theme_summary_confirm_retry():
    from scribe.council.wizard import ThemeInterviewer
    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene=None,
    )
    interviewer = ThemeInterviewer()
    import unittest.mock
    new_theme = ThemeSummary(
        genre="都市", emotion="温暖", protagonist="白领",
        desire="成功", conflict="人与人", setting="上海",
        effect="让读者思考", scene=None,
    )
    with unittest.mock.patch('builtins.input', side_effect=['n', '']):
        with unittest.mock.patch.object(interviewer, 'interview', return_value=new_theme):
            result = theme.confirm(interviewer)
    assert result.genre == "都市"


def test_council_wizard_build_topic():
    from scribe.council.wizard import CouncilWizard, ThemeSummary, WritingScope
    from unittest.mock import MagicMock

    theme = ThemeSummary(
        genre="仙侠", emotion="虐心", protagonist="魔尊",
        desire="自由", conflict="人与命运", setting="三界",
        effect="让读者哭", scene="大战后独坐山巅",
    )
    scope = WritingScope(mode="chapter", target="第三章", description="生成第三章")
    book = MagicMock()
    book.name = "测试书籍"

    wizard = CouncilWizard.__new__(CouncilWizard)
    topic = wizard._build_topic(theme, scope, book)

    assert "测试书籍" in topic
    assert "仙侠" in topic
    assert "魔尊" in topic
    assert "第三章" in topic
    assert "chapter" in topic


def test_council_wizard_select_writers_default():
    from scribe.council.wizard import CouncilWizard
    import unittest.mock

    wizard = CouncilWizard.__new__(CouncilWizard)
    recommended = ["jiulufeixiang", "priest"]

    with unittest.mock.patch('builtins.input', return_value=''):
        result = wizard._select_writers(recommended)
    assert result == recommended


def test_council_wizard_select_writers_custom():
    from scribe.council.wizard import CouncilWizard
    import unittest.mock

    wizard = CouncilWizard.__new__(CouncilWizard)
    recommended = ["jiulufeixiang", "priest"]

    with unittest.mock.patch('builtins.input', return_value='4,5'):
        result = wizard._select_writers(recommended)
    assert "san-san" in result
    assert "liu-cui-hu" in result
