from pathlib import Path

from agent_memory.migrate import import_legacy_workspace


def test_import_legacy_workspace_moves_daily_and_long_memory(tmp_path: Path):
    (tmp_path / 'memory').mkdir()
    (tmp_path / 'memory' / '2026-04-20.md').write_text('- 10:00 Decided to keep hot memory tiny\n', encoding='utf-8')
    (tmp_path / 'MEMORY.md').write_text('# MEMORY.md\n\n- Supports browser control independently\n', encoding='utf-8')

    result = import_legacy_workspace(tmp_path)

    assert result['episodic_imported'] >= 1
    assert result['core_imported'] >= 1
    assert (tmp_path / '.memory' / 'core' / 'capabilities.md').exists()
    assert (tmp_path / '.memory' / 'episodic' / '2026-04-20.md').exists()


def test_import_legacy_workspace_dedupes_similar_long_memory(tmp_path: Path):
    (tmp_path / 'memory').mkdir()
    (tmp_path / 'MEMORY.md').write_text(
        '# MEMORY.md\n\n- Supports browser control independently\n- Browser control is supported independently\n',
        encoding='utf-8',
    )

    result = import_legacy_workspace(tmp_path)
    capabilities = (tmp_path / '.memory' / 'core' / 'capabilities.md').read_text(encoding='utf-8')

    assert result['core_imported'] == 1
    assert capabilities.count('- ') == 1


def test_import_legacy_workspace_is_idempotent_for_core_memory(tmp_path: Path):
    (tmp_path / 'memory').mkdir()
    (tmp_path / 'MEMORY.md').write_text('# MEMORY.md\n\n- Supports browser control independently\n', encoding='utf-8')

    first = import_legacy_workspace(tmp_path)
    second = import_legacy_workspace(tmp_path)
    capabilities = (tmp_path / '.memory' / 'core' / 'capabilities.md').read_text(encoding='utf-8')

    assert first['core_imported'] == 1
    assert second['core_imported'] == 0
    assert capabilities.count('- ') == 1


def test_import_legacy_workspace_does_not_skip_on_substring_match(tmp_path: Path):
    (tmp_path / 'memory').mkdir()
    target = tmp_path / '.memory' / 'episodic'
    target.mkdir(parents=True)
    (target / '2026-04-20.md').write_text(
        '- 00:00 Decided to keep hot memory tiny and stable [category:decision source:import]\n',
        encoding='utf-8',
    )
    (tmp_path / 'memory' / '2026-04-20.md').write_text('- 10:00 Decided to keep hot memory tiny\n', encoding='utf-8')

    result = import_legacy_workspace(tmp_path)
    content = (target / '2026-04-20.md').read_text(encoding='utf-8')

    assert result['episodic_imported'] == 1
    assert 'Decided to keep hot memory tiny [category:decision source:import]' in content


def test_import_legacy_workspace_strips_flexible_timestamps(tmp_path: Path):
    (tmp_path / 'memory').mkdir()
    (tmp_path / 'memory' / '2026-04-20.md').write_text(
        '- 9:05 Keep hot memory small\n- 10:00   Supports browser recall\n',
        encoding='utf-8',
    )

    import_legacy_workspace(tmp_path)
    content = (tmp_path / '.memory' / 'episodic' / '2026-04-20.md').read_text(encoding='utf-8')

    assert '9:05' not in content
    assert '10:00   ' not in content
    assert 'Keep hot memory small' in content
    assert 'Supports browser recall' in content
