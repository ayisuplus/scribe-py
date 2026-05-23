import pytest
from unittest.mock import AsyncMock, MagicMock

from scribe.council.editor import EditorAgent
from scribe.council.debate_state import WriterDebateState, WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="最终方案：...", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def debate_state_with_history():
    state = WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是魔尊",
        rounds=2,
        max_rounds=2,
        writers=["a", "b"],
        history=[
            WriterOpinion(writer_id="a", writer_name="Writer A", round=1, content="观点A1", stance="suggest"),
            WriterOpinion(writer_id="b", writer_name="Writer B", round=1, content="观点B1", stance="support"),
            WriterOpinion(writer_id="a", writer_name="Writer A", round=2, content="观点A2", stance="oppose"),
            WriterOpinion(writer_id="b", writer_name="Writer B", round=2, content="观点B2", stance="neutral"),
        ],
        per_writer_history={"a": ["观点A1", "观点A2"], "b": ["观点B1", "观点B2"]},
        current_response="观点B2",
        final_proposal=None,
    )
    return state


def test_build_synthesis_prompt_contains_all_opinions(debate_state_with_history):
    editor = EditorAgent.__new__(EditorAgent)
    prompt = editor._build_synthesis_prompt(debate_state_with_history)
    assert "观点A1" in prompt
    assert "观点B1" in prompt
    assert "观点A2" in prompt
    assert "观点B2" in prompt


def test_build_synthesis_prompt_contains_topic(debate_state_with_history):
    editor = EditorAgent.__new__(EditorAgent)
    prompt = editor._build_synthesis_prompt(debate_state_with_history)
    assert "帮我看看这个角色" in prompt
    assert "主角是魔尊" in prompt


def test_build_synthesis_prompt_no_user_text():
    editor = EditorAgent.__new__(EditorAgent)
    state = WriterDebateState(
        topic="创作构思", user_text=None,
        rounds=1, max_rounds=1, writers=["a"],
        history=[WriterOpinion(writer_id="a", writer_name="A", round=1, content="test", stance="suggest")],
        per_writer_history={"a": ["test"]},
        current_response="test", final_proposal=None,
    )
    prompt = editor._build_synthesis_prompt(state)
    assert "（无" in prompt
