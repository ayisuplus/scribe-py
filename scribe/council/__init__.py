"""Writer Council — 多作家辩论系统"""

from scribe.council.debate_state import WriterOpinion, WriterDebateState
from scribe.council.router import WriterRouter
from scribe.council.writer_agent import WriterAgent, load_writer_persona
from scribe.council.editor import EditorAgent
from scribe.council.council import CouncilOrchestrator, CouncilConfig
from scribe.council.wizard import (
    ThemeInterviewer,
    ScopeParser,
    ThemeSummary,
    WritingScope,
    CouncilWizard,
)

__all__ = [
    "WriterOpinion",
    "WriterDebateState",
    "WriterRouter",
    "WriterAgent",
    "load_writer_persona",
    "EditorAgent",
    "CouncilOrchestrator",
    "CouncilConfig",
    "ThemeInterviewer",
    "ScopeParser",
    "ThemeSummary",
    "WritingScope",
    "CouncilWizard",
]
