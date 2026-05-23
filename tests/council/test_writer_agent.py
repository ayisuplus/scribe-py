import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from scribe.council.writer_agent import WriterAgent
from scribe.council.debate_state import WriterDebateState, WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="测试发言内容", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def sample_state():
    return WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是一个仙侠世界的魔尊",
        rounds=1,
        max_rounds=2,
        writers=["test_writer"],
        history=[],
        per_writer_history={"test_writer": []},
        current_response="",
        final_proposal=None,
    )


def test_extract_stance_support():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我同意这个观点，说得很好") == "support"


def test_extract_stance_oppose():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我反对，这样写不行") == "oppose"


def test_extract_stance_suggest():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("我建议可以试试另一种写法") == "suggest"


def test_extract_stance_neutral():
    agent = WriterAgent.__new__(WriterAgent)
    assert agent._extract_stance("这个角色还行吧") == "neutral"


def test_build_debate_prompt_contains_topic(mock_llm, sample_state):
    agent = WriterAgent.__new__(WriterAgent)
    agent.writer_id = "test"
    agent._persona = MagicMock()
    agent._persona.name = "Test Writer"

    prompt = agent._build_debate_prompt(sample_state)
    assert "帮我看看这个角色" in prompt
    assert "仙侠世界的魔尊" in prompt
