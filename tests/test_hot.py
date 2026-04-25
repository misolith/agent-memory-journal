from pathlib import Path

from agent_memory import Journal
from agent_memory.hot import rebuild_agent_md


def test_rebuild_agent_md_includes_only_pinned_items(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Pinned constraint should appear', category='constraint', pinned=True)
    journal.remember('Unpinned decision should not appear', category='decision', pinned=False)

    result = rebuild_agent_md(tmp_path / '.memory')
    content = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert result['written'] == 1
    assert 'Pinned constraint should appear' in content
    assert 'Unpinned decision should not appear' not in content


def test_rebuild_agent_md_enforces_char_limit(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('A' * 150, category='constraint', pinned=True)
    journal.remember('B' * 150, category='decision', pinned=True)

    result = rebuild_agent_md(tmp_path / '.memory', max_chars=200)
    content = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert result['written'] == 1
    assert result['skipped'] == 1
    assert 'AAAAAAAA' in content or 'BBBBBBBB' in content


def test_rebuild_agent_md_caller_arg_overrides_config(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('C' * 150, category='constraint', pinned=True)
    journal.remember('D' * 150, category='decision', pinned=True)

    result = rebuild_agent_md(tmp_path / '.memory', max_chars=200)

    assert result['max_chars'] == 200
    assert result['written'] == 1


def test_rebuild_agent_md_strips_metadata_from_hot_file(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Hot claim must stay tiny', category='constraint', pinned=True)

    rebuild_agent_md(tmp_path / '.memory')
    content = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert 'Hot claim must stay tiny' in content
    # Metadata flags belong in core/, not in the hot surface that the agent loads.
    assert 'id:' not in content
    assert 'state:' not in content
    assert 'pinned:true' not in content
