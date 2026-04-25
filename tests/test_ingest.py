from pathlib import Path

from agent_memory import Journal
from agent_memory.ingest import ingest_cycle


def test_ingest_cycle_promotes_and_rebuilds_hot_set(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.note_v2('Use v2 memory as development telemetry', category='decision', importance='high')
    episodic = tmp_path / '.memory' / 'episodic'
    episodic.mkdir(parents=True, exist_ok=True)
    (episodic / '2026-04-24.md').write_text('- 10:00 Use v2 memory as development telemetry [category:decision importance:high source:agent]\n', encoding='utf-8')
    journal.remember_v2('Pinned hot constraint', category='constraint', pinned=True)

    report = ingest_cycle(tmp_path / '.memory')

    decisions = (tmp_path / '.memory' / 'core' / 'decisions.md').read_text(encoding='utf-8')
    hot = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert report.promoted_count >= 1
    assert report.hot_written == 1
    assert report.review_status == 'OK'
    assert 'Use v2 memory as development telemetry' in decisions
    assert 'Pinned hot constraint' in hot
