from agent_memory import Journal
from agent_memory.ingest import ingest_cycle


def test_core_memory_includes_id_state_and_created_metadata(tmp_path):
    journal = Journal(root=tmp_path)
    journal.remember('Pinned constraint for metadata', category='constraint', pinned=True)
    content = (tmp_path / '.memory' / 'core' / 'constraints.md').read_text(encoding='utf-8')
    assert 'id:' in content
    assert 'state:active' in content
    assert 'created:' in content


def test_ingest_does_not_duplicate_same_core_id(tmp_path):
    journal = Journal(root=tmp_path)
    journal.note('Use v2 memory as development telemetry', category='decision', importance='high')
    episodic = tmp_path / '.memory' / 'episodic'
    episodic.mkdir(parents=True, exist_ok=True)
    (episodic / '2026-04-24.md').write_text('- 10:00 Use v2 memory as development telemetry [category:decision importance:high source:agent]\n', encoding='utf-8')
    ingest_cycle(tmp_path / '.memory')
    ingest_cycle(tmp_path / '.memory')
    decisions = (tmp_path / '.memory' / 'core' / 'decisions.md').read_text(encoding='utf-8')
    assert decisions.count('Use v2 memory as development telemetry') == 1
