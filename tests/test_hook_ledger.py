"""
Tests for scribe.memory.hook_ledger module.
"""

import tempfile
from pathlib import Path

import pytest

from scribe.types import HookEntry, HookStatus
from scribe.memory.hook_ledger import HookLedgerManager


class TestHookLedgerManager:
    """Test HookLedgerManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def ledger_path(self, temp_dir):
        """Get path for ledger file."""
        return temp_dir / "hooks.json"

    def test_load_empty_ledger(self, ledger_path):
        """Test loading a non-existent ledger creates empty one."""
        manager = HookLedgerManager.load(ledger_path)
        
        assert len(manager.ledger().hooks) == 0

    def test_add_hook(self, ledger_path):
        """Test adding a hook."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "神秘信件", 1)
        
        assert len(manager.ledger().hooks) == 1
        assert manager.ledger().hooks[0].id == "H001"
        assert manager.ledger().hooks[0].seed_chapter == 1
        assert manager.ledger().hooks[0].status == HookStatus.PLANTED

    def test_get_by_status(self, ledger_path):
        """Test getting hooks by status."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "神秘信件", 1)
        manager.add_hook("H002", "失踪的戒指", 2)
        manager.add_hook("H003", "另一个钩子", 3)
        manager.update_status("H002", HookStatus.PRESSURED, 4)
        
        planted = manager.get_by_status(HookStatus.PLANTED)
        pressured = manager.get_by_status(HookStatus.PRESSURED)
        
        assert len(planted) == 2
        assert len(pressured) == 1
        assert pressured[0].id == "H002"

    def test_update_status(self, ledger_path):
        """Test updating hook status."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "test", 1)
        manager.update_status("H001", HookStatus.PRESSURED, 3)
        
        hook = manager.ledger().hooks[0]
        assert hook.status == HookStatus.PRESSURED
        assert hook.last_mention_chapter == 3

    def test_record_payoff(self, ledger_path):
        """Test recording payoff text."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "test", 1)
        manager.record_payoff("H001", "信被烧毁", 5)
        
        hook = manager.ledger().hooks[0]
        assert hook.status == HookStatus.RESOLVED
        assert hook.payoff_text == "信被烧毁"
        assert hook.last_mention_chapter == 5

    def test_get_overdue(self, ledger_path):
        """Test getting overdue hooks."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "old hook", 1)
        manager.add_hook("H002", "new hook", 8)
        
        overdue = manager.get_overdue(current_chapter=10, max_gap=5)
        
        assert len(overdue) == 1
        assert overdue[0].id == "H001"

    def test_save_and_load(self, ledger_path):
        """Test save and load round-trip."""
        # Create and save
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "神秘信件", 1)
        manager.add_hook("H002", "失踪的戒指", 2)
        manager.update_status("H002", HookStatus.PRESSURED, 4)
        manager.save()
        
        # Load in new manager
        manager2 = HookLedgerManager.load(ledger_path)
        
        assert len(manager2.ledger().hooks) == 2
        assert manager2.ledger().hooks[0].id == "H001"
        assert manager2.ledger().hooks[1].status == HookStatus.PRESSURED

    def test_build_hook_prompt(self, ledger_path):
        """Test building hook prompt."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "神秘信件", 1)
        manager.add_hook("H002", "失踪戒指", 2)
        manager.update_status("H002", HookStatus.PRESSURED, 4)
        
        prompt = manager.build_hook_prompt()
        
        assert "伏笔账本" in prompt
        assert "H001" in prompt
        assert "H002" in prompt
        assert "已种下" in prompt
        assert "正在施压" in prompt

    def test_build_hook_prompt_empty(self, ledger_path):
        """Test empty ledger produces empty prompt."""
        manager = HookLedgerManager.load(ledger_path)
        
        prompt = manager.build_hook_prompt()
        
        assert prompt == ""

    def test_deferred_hooks_in_prompt(self, ledger_path):
        """Test deferred hooks appear in prompt."""
        manager = HookLedgerManager.load(ledger_path)
        manager.add_hook("H001", "神秘信件", 1)
        manager.add_hook("H002", "暂缓事件", 2)
        manager.update_status("H002", HookStatus.DEFERRED, None)
        
        prompt = manager.build_hook_prompt()
        
        assert "暂缓" in prompt
        assert "H002" in prompt


class TestHookEntry:
    """Test HookEntry structure."""

    def test_hook_entry_defaults(self):
        """Test HookEntry default values."""
        entry = HookEntry(
            id="H001",
            description="test",
            seed_chapter=1,
            status=HookStatus.PLANTED,
        )
        
        assert entry.last_mention_chapter is None
        assert entry.payoff_text is None
