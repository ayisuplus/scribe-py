import pytest
from scribe.council.router import WriterRouter


@pytest.fixture
def router():
    return WriterRouter()


def test_recommend_xianxia(router):
    result = router.recommend("帮我写一段仙侠小说的开头")
    assert "jiulufeixiang" in result or "mo-xiang-tong-xiu" in result


def test_recommend_urban(router):
    result = router.recommend("写一个都市职场故事")
    assert "liu-cui-hu" in result or "mei-shi-niang" in result


def test_recommend_scifi(router):
    result = router.recommend("科幻题材的创作构思")
    assert "priest" in result


def test_recommend_pure_literature(router):
    result = router.recommend("纯文学短篇小说")
    assert "san-san" in result


def test_recommend_with_user_text(router):
    result = router.recommend("帮我看看", "这是一个关于仙侠和言情的故事")
    assert "jiulufeixiang" in result


def test_recommend_minimum_two(router):
    result = router.recommend("随便什么题材")
    assert len(result) >= 2


def test_recommend_max_three(router):
    result = router.recommend("仙侠言情古装轻喜剧虐心")
    assert len(result) <= 3
