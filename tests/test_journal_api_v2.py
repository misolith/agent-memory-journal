import pytest

from agent_memory import Journal
from agent_memory.api import LegacyJournal


def test_v2_journal_primary_flow(tmp_path):
    journal = Journal(root=tmp_path)
    journal.init()
    journal.note('Decision: keep AGENT hot set tiny', category='decision', importance='high')
    journal.remember('Pinned constraint for hot set', category='constraint', pinned=True)
    journal.session_note('review-1', 'Pinned detection is too loose', category='gotcha', importance='high')

    hits = journal.recall_core('pinned constraint', k=5)
    warm_hits = journal.recall('pinned constraint', k=5, tier='warm')
    ingest = journal.ingest()
    review_log = journal.log_review_findings('review-2', ['Thresholds are duplicated'])

    assert hits
    assert warm_hits
    assert ingest.hot_written >= 1
    assert review_log.notes_written == 1


def test_journal_recall_all_merges_warm_and_cold(tmp_path):
    journal = Journal(root=tmp_path)
    journal.init()
    journal.remember('Pinned constraint for hot set', category='constraint', pinned=True)
    legacy = LegacyJournal(root=tmp_path)
    legacy.note('Cold legacy note about pinned constraint')

    hits = journal.recall('pinned constraint', k=10, tier='all')
    joined = ' || '.join(item.text for item in hits)

    assert 'Pinned constraint for hot set' in joined
    assert 'Cold legacy note about pinned constraint' in joined


def test_v2_journal_works_with_memory_root(tmp_path):
    memory_root = tmp_path / '.memory'
    journal = Journal(root=memory_root)
    journal.init()
    journal.remember('Pinned constraint for direct memory root', category='constraint', pinned=True)
    hits = journal.recall_core('direct memory root', k=5)
    assert hits
    assert not (memory_root / '.memory').exists()


def test_v2_journal_recall_limit_semantics(tmp_path):
    journal = Journal(root=tmp_path)
    journal.remember('Pinned constraint for hot set', category='constraint', pinned=True)
    assert journal.recall_core('constraint', k=0) == []
    with pytest.raises(ValueError):
        journal.recall_core('constraint', k=-1)


def test_legacy_journal_still_available(tmp_path):
    legacy = LegacyJournal(root=tmp_path)
    note = legacy.note('Legacy note remains available')
    assert note.exists()
