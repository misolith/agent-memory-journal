from pathlib import Path

from agent_memory import Journal
from agent_memory.normalize import claims_match, normalize_claim


def test_normalize_claim_reduces_surface_variation():
    normalized, tokens = normalize_claim("Now supports exact memory windows and reviewed promotions")
    assert "support" in normalized or "supports" in normalized
    assert "memory" in tokens
    assert "window" in normalized or "windows" in normalized


def test_claims_match_handles_simple_paraphrase():
    a = "Memory review now supports exact window filtering"
    b = "Exact filtering windows are now supported for memory review"
    assert claims_match(a, b)


def test_journal_recall_matches_token_overlap(tmp_path: Path):
    (tmp_path / "MEMORY.md").write_text("# MEMORY.md\n\n- exact memory windows are now supported\n", encoding="utf-8")
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "2026-04-24.md").write_text("- 10:00 reviewed promotions stay small\n", encoding="utf-8")

    journal = Journal(root=tmp_path)
    hits = journal.recall("supports exact memory window", k=3, tier="warm")

    assert hits
    assert "exact memory windows" in hits[0].text
