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
