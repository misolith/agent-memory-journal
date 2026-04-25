from pathlib import Path

from agent_memory import Journal
from agent_memory.decay import archive_unpinned_core


def test_decay_archives_stale_entries_by_age(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init()
    core = tmp_path / '.memory' / 'core' / 'constraints.md'
    core.write_text(
        '# Constraints\n\n'
        '- old constraint [id:con-old state:active source:agent created:2025-01-01T10:00:00]\n'
        '- fresh constraint [id:con-new state:active source:agent created:2099-01-01T00:00:00+00:00]\n',
        encoding='utf-8',
    )
    report = archive_unpinned_core(tmp_path / '.memory', max_age_days=30, max_active_per_file=50)
    archived = (tmp_path / '.memory' / 'archive' / 'core' / 'constraints.md').read_text(encoding='utf-8')
    active = core.read_text(encoding='utf-8')
    assert report.archived == 1
    assert 'old constraint' in archived
    assert 'fresh constraint' in active
