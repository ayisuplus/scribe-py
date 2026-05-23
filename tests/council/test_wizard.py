import pytest
from scribe.council.wizard import ThemeSummary, WritingScope, ScopeParser


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
