import pytest

from agent_memory import Journal


def test_journal_exposes_v2_helper_methods(tmp_path):
    journal = Journal(root=tmp_path)
    journal.init_v2()
    journal.note_v2('Decision: keep AGENT hot set tiny', category='decision', importance='high')
    journal.remember_v2('Pinned constraint for hot set', category='constraint', pinned=True)
    journal.session_note('review-1', 'Pinned detection is too loose', category='gotcha', importance='high')

    hits = journal.recall_core('pinned constraint', k=5)
    ingest = journal.ingest()
    review_log = journal.log_review_findings('review-2', ['Thresholds are duplicated'])

    assert hits
    assert ingest.hot_written >= 1
    assert review_log.notes_written == 1


def test_journal_v2_helpers_work_when_root_is_memory_dir(tmp_path):
    memory_root = tmp_path / '.memory'
    journal = Journal(root=memory_root)
    journal.init_v2()
    journal.remember_v2('Pinned constraint for direct memory root', category='constraint', pinned=True)

    hits = journal.recall_core('direct memory root', k=5)
    ingest = journal.ingest()
    review_log = journal.log_review_findings('review/root', ['Blank', 'Pinned detection drift'])

    assert hits
    assert ingest.hot_written >= 1
    assert review_log.session_id == 'reviewroot'
    assert (memory_root / 'sessions' / 'reviewroot.md').exists()
    assert not (memory_root / '.memory').exists()


def test_journal_recall_core_preserves_limit_semantics(tmp_path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Pinned constraint for hot set', category='constraint', pinned=True)

    assert journal.recall_core('constraint', k=0) == []
    with pytest.raises(ValueError):
        journal.recall_core('constraint', k=-1)


def test_journal_log_review_findings_skips_blank_entries(tmp_path):
    journal = Journal(root=tmp_path)
    report = journal.log_review_findings('review-blank', ['  ', 'Actual finding', ''])

    assert report.notes_written == 1
    assert report.session_id == 'review-blank'
