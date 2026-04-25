from pathlib import Path

import pytest

from agent_memory import Journal
from agent_memory.core_recall import recall_core


def test_recall_core_finds_relevant_core_entries(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Keep AGENT.md tiny and pinned', category='constraint', pinned=True)
    journal.remember_v2('Supports browser control independently', category='capability', pinned=False)

    hits = recall_core(tmp_path / '.memory', 'browser control', k=3)

    assert hits
    assert hits[0].category == 'capability'
    assert 'browser control' in hits[0].text.lower()


def test_recall_core_ranks_overlap_above_irrelevant_entries(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Promotion threshold must stay visible', category='constraint', pinned=False)
    journal.remember_v2('Keep AGENT.md tiny', category='constraint', pinned=True)

    hits = recall_core(tmp_path / '.memory', 'promotion threshold', k=2)

    assert len(hits) == 1
    assert 'Promotion threshold must stay visible' in hits[0].text


def test_recall_core_blank_query_returns_empty_list(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Supports browser control independently', category='capability', pinned=False)

    assert recall_core(tmp_path / '.memory', '   ', k=5) == []


def test_recall_core_k_zero_returns_empty_list(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Supports browser control independently', category='capability', pinned=False)

    assert recall_core(tmp_path / '.memory', 'browser', k=0) == []


def test_recall_core_negative_k_raises(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Supports browser control independently', category='capability', pinned=False)

    with pytest.raises(ValueError):
        recall_core(tmp_path / '.memory', 'browser', k=-1)


def test_recall_core_does_not_create_layout_on_missing_root(tmp_path: Path):
    missing_root = tmp_path / '.memory'

    hits = recall_core(missing_root, 'browser', k=3)

    assert hits == []
    assert not missing_root.exists()
