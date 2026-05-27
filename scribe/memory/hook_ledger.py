"""
Hook ledger manager for tracking foreshadowing elements.

Ports scribe-memory/src/hook_ledger.rs to Python.
"""

from __future__ import annotations

import json
from pathlib import Path

from scribe.types import HookEntry, HookLedger, HookStatus


class HookLedgerManager:
    """
    Manages a ledger of foreshadowing hooks across chapters.

    Tracks planted, pressured, resolved, and deferred hooks.
    Provides persistence via JSON file.
    """

    def __init__(self, ledger: HookLedger, path: Path):
        self._ledger = ledger
        self.path = path

    @staticmethod
    def load(path: Path) -> HookLedgerManager:
        """
        Load or create a hook ledger from a JSON file.

        If the file doesn't exist, creates an empty ledger.
        """
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                ledger = HookLedger.from_dict(json.loads(content))
            except Exception:
                ledger = HookLedger()
        else:
            ledger = HookLedger()

        return HookLedgerManager(ledger=ledger, path=path)

    def save(self) -> None:
        """
        Save the ledger to disk.

        Creates parent directories if needed.
        """
        if self.path.parent != self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "hooks": [
                {
                    "id": h.id,
                    "description": h.description,
                    "seed_chapter": h.seed_chapter,
                    "status": h.status.value,
                    "last_mention_chapter": h.last_mention_chapter,
                    "payoff_text": h.payoff_text,
                }
                for h in self._ledger.hooks
            ]
        }

        content = json.dumps(data, indent=2, ensure_ascii=False)
        self.path.write_text(content, encoding="utf-8")

    def add_hook(self, hook_id: str, description: str, seed_chapter: int) -> None:
        """
        Add a new hook to the ledger.
        """
        entry = HookEntry(
            id=hook_id,
            description=description,
            seed_chapter=seed_chapter,
            status=HookStatus.PLANTED,
            last_mention_chapter=None,
            payoff_text=None,
        )
        self._ledger.hooks.append(entry)

    def update_status(
        self,
        hook_id: str,
        status: HookStatus,
        chapter: int | None = None,
    ) -> None:
        """
        Update the status of a hook.

        Args:
            hook_id: The hook's ID
            status: The new status
            chapter: Optional chapter number for last mention
        """
        for hook in self._ledger.hooks:
            if hook.id == hook_id:
                hook.status = status
                hook.last_mention_chapter = chapter
                return

        raise ValueError(f"Hook {hook_id} not found")

    def record_payoff(
        self,
        hook_id: str,
        text: str,
        chapter: int,
    ) -> None:
        """
        Record the payoff text for a hook and mark it as resolved.

        Args:
            hook_id: The hook's ID
            text: The payoff text describing how the hook was resolved
            chapter: The chapter where the payoff occurs
        """
        for hook in self._ledger.hooks:
            if hook.id == hook_id:
                hook.payoff_text = text
                hook.last_mention_chapter = chapter
                hook.status = HookStatus.RESOLVED
                return

        raise ValueError(f"Hook {hook_id} not found")

    def get_by_status(self, status: HookStatus) -> list[HookEntry]:
        """Get all hooks with a given status."""
        return [h for h in self._ledger.hooks if h.status == status]

    def get_overdue(self, current_chapter: int, max_gap: int) -> list[HookEntry]:
        """
        Get hooks that are overdue (planted/pressured for too many chapters).

        Args:
            current_chapter: The current chapter number
            max_gap: Maximum allowed chapter gap since planting

        Returns:
            List of overdue hooks
        """
        overdue: list[HookEntry] = []

        for hook in self._ledger.hooks:
            if hook.status in (HookStatus.PLANTED, HookStatus.PRESSURED):
                gap = current_chapter - hook.seed_chapter
                if gap > max_gap:
                    overdue.append(hook)

        return overdue

    def build_hook_prompt(self) -> str:
        """
        Build a prompt fragment listing active hooks.

        Returns:
            A formatted string with all active (planted/pressured/deferred) hooks
        """
        planted = self.get_by_status(HookStatus.PLANTED)
        pressured = self.get_by_status(HookStatus.PRESSURED)
        deferred = self.get_by_status(HookStatus.DEFERRED)

        if not planted and not pressured and not deferred:
            return ""

        sections = ["## 伏笔账本"]

        if planted:
            items = [
                f"- [{h.id}] {h.description} (第{h.seed_chapter}章种下)"
                for h in planted
            ]
            sections.append("已种下：\n" + "\n".join(items))

        if pressured:
            items = [
                f"- [{h.id}] {h.description} (第{h.seed_chapter}章种下)"
                for h in pressured
            ]
            sections.append("正在施压：\n" + "\n".join(items))

        if deferred:
            items = [f"- [{h.id}] {h.description} (暂缓)" for h in deferred]
            sections.append("暂缓：\n" + "\n".join(items))

        return "\n\n".join(sections)

    def ledger(self) -> HookLedger:
        """Get the underlying ledger for serialization/testing."""
        return self._ledger


def from_dict(data: dict) -> HookLedger:
    """Create HookLedger from dictionary."""
    hooks = []
    for h_data in data.get("hooks", []):
        hooks.append(
            HookEntry(
                id=h_data["id"],
                description=h_data["description"],
                seed_chapter=h_data["seed_chapter"],
                status=HookStatus(h_data["status"]),
                last_mention_chapter=h_data.get("last_mention_chapter"),
                payoff_text=h_data.get("payoff_text"),
            )
        )
    return HookLedger(hooks=hooks)
