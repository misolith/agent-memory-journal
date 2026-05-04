from pathlib import Path

from agent_memory import Journal
from agent_memory.promote import collect_candidates, promote_repeated_candidates


def test_collect_candidates_merges_simple_paraphrases(tmp_path: Path):
    journal = Journal(root=tmp_path)
    first = journal.note('Memory review now supports exact window filtering', category='capability', importance='high')
    older = tmp_path / '.memory' / 'episodic' / '2026-04-24.md'
    older.write_text('- 09:00 Exact filtering windows are now supported for memory review [category:capability importance:high source:agent]\n', encoding='utf-8')

    candidates = collect_candidates(tmp_path / '.memory')
    assert candidates
    top = candidates[0]
    assert top.category == 'capability'
    assert top.distinct_days == 2
    assert top.occurrences == 2


def test_promote_repeated_candidates_promotes_to_core(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.note('Main branch must stay stable during the rewrite', category='constraint', importance='high')
    episodic = tmp_path / '.memory' / 'episodic'
    (episodic / '2026-04-24.md').write_text('- 08:00 Main branch must remain stable during rewrite work [category:constraint importance:high source:agent]\n', encoding='utf-8')

    promoted = promote_repeated_candidates(tmp_path / '.memory')
    assert promoted

    constraints = (tmp_path / '.memory' / 'core' / 'constraints.md').read_text(encoding='utf-8')
    assert 'Main branch must stay stable' in constraints or 'Main branch must remain stable' in constraints


def test_collect_candidates_merges_high_overlap_claims(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.note('Constraint: report only after code, commit, push, or a real blocker, not after intention alone.', category='constraint', importance='high')
    episodic = tmp_path / '.memory' / 'episodic'
    (episodic / '2026-04-24.md').write_text('- 08:00 Report only after visible progress or a blocker, never after intent alone [category:constraint importance:high source:agent]\n', encoding='utf-8')

    candidates = collect_candidates(tmp_path / '.memory', match_threshold=0.60, overlap_threshold=0.5)
    assert candidates[0].distinct_days == 2
    assert candidates[0].occurrences == 2
