from pathlib import Path

from agent_memory import Journal
from agent_memory.hot import rebuild_agent_md


def test_rebuild_agent_md_includes_only_pinned_items(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Pinned constraint should appear', category='constraint', pinned=True)
    journal.remember_v2('Unpinned decision should not appear', category='decision', pinned=False)

    result = rebuild_agent_md(tmp_path / '.memory')
    content = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert result['written'] == 1
    assert 'Pinned constraint should appear' in content
    assert 'Unpinned decision should not appear' not in content


def test_rebuild_agent_md_enforces_char_limit(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('A' * 80, category='constraint', pinned=True)
    journal.remember_v2('B' * 80, category='decision', pinned=True)

    result = rebuild_agent_md(tmp_path / '.memory', max_chars=200)
    content = (tmp_path / '.memory' / 'AGENT.md').read_text(encoding='utf-8')

    assert result['written'] == 1
    assert result['skipped'] == 1
    assert 'AAAAAAAA' in content or 'BBBBBBBB' in content
