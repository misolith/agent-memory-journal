from pathlib import Path

from agent_memory import Journal
from agent_memory.storage import init_memory_root


def test_init_memory_root_creates_v2_layout(tmp_path: Path):
    root = tmp_path / ".memory"
    paths = init_memory_root(root)

    assert paths.hot_file.exists()
    assert (root / "core" / "decisions.md").exists()
    assert (root / "episodic").exists()
    assert (root / "sessions").exists()
    assert (root / "archive" / "core").exists()
    assert (root / "index" / "manifest.json").exists()


def test_journal_can_write_v2_episodic_and_core(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init_v2()

    episodic_path = journal.note_v2("Adopted v2 storage for dogfooding", category="decision", importance="high")
    core_path = journal.remember_v2("AGENT.md must stay tiny", category="constraint", pinned=True)

    assert episodic_path.exists()
    assert core_path.exists()
    assert "Adopted v2 storage" in episodic_path.read_text(encoding="utf-8")
    assert "pinned:true" in core_path.read_text(encoding="utf-8")
