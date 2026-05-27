"""Writer Council — 多作家辩论系统"""

from scribe.council.council import CouncilConfig, CouncilOrchestrator
from scribe.council.debate_state import WriterDebateState, WriterOpinion
from scribe.council.editor import EditorAgent
from scribe.council.router import WriterRouter
from scribe.council.wizard import (
    CouncilWizard,
    ScopeParser,
    ThemeInterviewer,
    ThemeSummary,
    WritingScope,
)
from scribe.council.writer_agent import WriterAgent, load_writer_persona

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
