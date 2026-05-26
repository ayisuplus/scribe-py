import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from scribe.council.council import CouncilOrchestrator, CouncilConfig
from scribe.council.debate_state import WriterOpinion


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(content="测试内容", tool_calls=None))
    llm.max_context_tokens = MagicMock(return_value=8000)
    return llm


@pytest.fixture
def council_config():
    return CouncilConfig(
        max_rounds=2,
        model="test-model",
        writer_dir=Path("writers/"),
    )


def test_council_config_defaults():
    config = CouncilConfig()
    assert config.max_rounds == 2
    assert config.model == "gpt-4o"


def test_register_writer(mock_llm, council_config, tmp_path):
    (tmp_path / "identity.md").write_text("Test identity", encoding="utf-8")
    (tmp_path / "ishiki.md").write_text("Test ishiki", encoding="utf-8")
    council = CouncilOrchestrator(mock_llm, council_config)
    council.register_writer("test", tmp_path)
    assert "test" in council._writers


@pytest.mark.asyncio
async def test_council_run(mock_llm, council_config):
    """集成测试：模拟完整辩论流程"""
    council = CouncilOrchestrator(mock_llm, council_config)

    # Mock WriterAgent
    mock_writer = MagicMock()
    mock_writer.debate = AsyncMock(return_value=WriterOpinion(
        writer_id="test", writer_name="Test",
        round=1, content="test opinion", stance="suggest",
    ))
    mock_writer.writer_id = "test"
    council._writers["test"] = mock_writer

    # Mock EditorAgent
    council._editor.synthesize = AsyncMock(return_value="最终方案")

    result = await council.run(
        topic="测试主题",
        writer_ids=["test"],
        max_rounds=1,
    )

    assert result == "最终方案"
    assert mock_writer.debate.call_count == 1
    council._editor.synthesize.assert_called_once()
