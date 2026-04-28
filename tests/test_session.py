from datetime import datetime, timezone
from pathlib import Path

from agent_memory import Journal
from agent_memory.session import collect_session_candidates


def test_session_note_writes_scoped_file(tmp_path: Path):
    journal = Journal(root=tmp_path)
    target = journal.session_note('alpha-1', 'Shared blocker around promotion threshold', category='gotcha', importance='high')

    assert target.exists()
    content = target.read_text(encoding='utf-8')
    assert 'Shared blocker around promotion threshold' in content
    assert 'category:gotcha' in content


def test_collect_session_candidates_merges_across_sessions(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.session_note('alpha', 'Promotion threshold needs to be visible in docs', category='constraint', importance='high')
    journal.session_note('beta', 'Docs must show the promotion threshold clearly', category='constraint', importance='high')

    candidates = collect_session_candidates(tmp_path / '.memory')
    assert candidates
    assert candidates[0].occurrences == 2
    assert candidates[0].distinct_days == 2


def test_prune_sessions_archives_only_stale_files(tmp_path: Path):
    journal = Journal(root=tmp_path)
    old_path = journal.session_note('alpha', 'Old transient context')
    keep_path = journal.session_note('beta', 'Fresh transient context')

    stale = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    fresh = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc).timestamp()
    old_path.touch()
    keep_path.touch()
    import os
    os.utime(old_path, (stale, stale))
    os.utime(keep_path, (fresh, fresh))

    result = journal.prune_sessions(days=7, now=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc))

    assert result.archived == ['alpha.md']
    assert result.kept == ['beta.md']
    assert not old_path.exists()
    assert keep_path.exists()
    assert (tmp_path / '.memory' / 'archive' / 'sessions' / 'alpha.md').exists()


def test_prune_sessions_dry_run_leaves_files_in_place(tmp_path: Path):
    journal = Journal(root=tmp_path)
    target = journal.session_note('alpha', 'Old transient context')

    stale = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    import os
    os.utime(target, (stale, stale))

    result = journal.prune_sessions(days=7, now=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc), dry_run=True)

    assert result.archived == ['alpha.md']
    assert target.exists()
    assert not (tmp_path / '.memory' / 'archive' / 'sessions' / 'alpha.md').exists()
