from pathlib import Path

from agent_memory import Journal
from agent_memory.decay import archive_unpinned_core


def test_archive_unpinned_core_moves_excess_bullets(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init()
    for i in range(4):
        journal.remember(f'Constraint {i}', category='constraint', pinned=False)
    journal.remember('Pinned constraint', category='constraint', pinned=True)

    report = archive_unpinned_core(tmp_path / '.memory', max_active_per_file=3)
    core = (tmp_path / '.memory' / 'core' / 'constraints.md').read_text(encoding='utf-8')
    archive = (tmp_path / '.memory' / 'archive' / 'core' / 'constraints.md').read_text(encoding='utf-8')

    assert report.archived == 2
    assert 'Pinned constraint' in core
    assert 'Constraint 3' in core
    assert 'Constraint 0' in archive


def test_archive_unpinned_core_keeps_all_when_under_limit(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Only one decision', category='decision', pinned=False)

    report = archive_unpinned_core(tmp_path / '.memory', max_active_per_file=5)

    assert report.archived == 0
    assert report.retained >= 1


def test_archive_unpinned_core_ignores_pinned_text_outside_metadata(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init()
    core_file = tmp_path / '.memory' / 'core' / 'constraints.md'
    with core_file.open('a', encoding='utf-8') as handle:
        handle.write('- avoid literal pinned:true in docs [source:agent]\n')
        handle.write('- real pinned item [source:agent pinned:true]\n')

    report = archive_unpinned_core(tmp_path / '.memory', max_active_per_file=1)
    core = core_file.read_text(encoding='utf-8')
    archive = (tmp_path / '.memory' / 'archive' / 'core' / 'constraints.md').read_text(encoding='utf-8')

    assert report.archived == 1
    assert 'real pinned item' in core
    assert 'avoid literal pinned:true in docs' in archive


def test_archive_unpinned_core_is_idempotent(tmp_path: Path):
    journal = Journal(root=tmp_path)
    for i in range(4):
        journal.remember(f'Decision {i}', category='decision', pinned=False)

    first = archive_unpinned_core(tmp_path / '.memory', max_active_per_file=2)
    second = archive_unpinned_core(tmp_path / '.memory', max_active_per_file=2)

    assert first.archived == 2
    assert second.archived == 0
