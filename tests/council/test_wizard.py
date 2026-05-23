import pytest
from scribe.council.wizard import ThemeSummary, WritingScope


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
