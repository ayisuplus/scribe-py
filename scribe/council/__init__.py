"""
Writer Council - multi-writer persona management for Scribe.

Inspired by nuwa-skill (https://github.com/alchaincyf/nuwa-skill).
"""

from scribe.council.registry import WriterRegistry, Writer, WriterGenre
from scribe.council.distiller import WriterDistiller

__all__ = [
    "WriterRegistry",
    "Writer",
    "WriterGenre",
    "WriterDistiller",
]