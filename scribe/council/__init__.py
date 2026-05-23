"""Writer Council — 多作家辩论系统"""

from scribe.council.debate_state import WriterOpinion, WriterDebateState
from scribe.council.router import WriterRouter
from scribe.council.writer_agent import WriterAgent
from scribe.council.editor import EditorAgent
from scribe.council.council import CouncilOrchestrator, CouncilConfig

__all__ = [
    "WriterOpinion",
    "WriterDebateState",
    "WriterRouter",
    "WriterAgent",
    "EditorAgent",
    "CouncilOrchestrator",
    "CouncilConfig",
]
