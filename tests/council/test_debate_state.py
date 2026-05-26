# tests/council/test_debate_state.py
from scribe.council.debate_state import WriterOpinion, WriterDebateState


def test_writer_opinion_creation():
    op = WriterOpinion(
        writer_id="jiulufeixiang",
        writer_name="九鹭非香",
        round=1,
        content="我觉得这个角色需要更多背景",
        stance="suggest",
    )
    assert op.writer_id == "jiulufeixiang"
    assert op.round == 1
    assert op.stance == "suggest"


def test_debate_state_creation():
    state = WriterDebateState(
        topic="帮我看看这个角色",
        user_text="主角是一个仙侠世界的魔尊",
        rounds=0,
        max_rounds=2,
        writers=["jiulufeixiang", "mo-xiang-tong-xiu"],
        history=[],
        per_writer_history={"jiulufeixiang": [], "mo-xiang-tong-xiu": []},
        current_response="",
        final_proposal=None,
    )
    assert state.max_rounds == 2
    assert len(state.writers) == 2
    assert state.final_proposal is None


def test_debate_state_update():
    state = WriterDebateState(
        topic="test",
        user_text=None,
        rounds=0,
        max_rounds=2,
        writers=["a", "b"],
        history=[],
        per_writer_history={"a": [], "b": []},
        current_response="",
        final_proposal=None,
    )
    op = WriterOpinion(
        writer_id="a", writer_name="Writer A",
        round=1, content="test opinion", stance="support",
    )
    state.history.append(op)
    state.per_writer_history["a"].append(op.content)
    state.current_response = op.content
    state.rounds = 1

    assert len(state.history) == 1
    assert state.per_writer_history["a"] == ["test opinion"]
    assert state.current_response == "test opinion"
    assert state.rounds == 1
