from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_memory import Journal
from agent_memory.ingest import ingest_cycle


def _backdate_line(line: str, iso: str) -> str:
    line = re.sub(r'created:[^\s\]]+', f'created:{iso}', line)
    line = re.sub(r'last_seen:[^\s\]]+', f'last_seen:{iso}', line)
    return line


def test_ingest_cycle_archives_stale_unpinned_core(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Recent decision', category='decision')
    journal.remember('Stale decision to be archived', category='decision')

    decisions = tmp_path / '.memory' / 'core' / 'decisions.md'
    stale_iso = (datetime.now(timezone.utc) - timedelta(days=60)).replace(microsecond=0).isoformat()
    new_lines = []
    for line in decisions.read_text(encoding='utf-8').splitlines():
        if 'Stale decision to be archived' in line:
            line = _backdate_line(line, stale_iso)
        new_lines.append(line)
    decisions.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')

    report = ingest_cycle(tmp_path / '.memory')
    assert report.archived_count >= 1, report
    archived_file = tmp_path / '.memory' / 'archive' / 'core' / 'decisions.md'
    assert archived_file.exists()
    assert 'Stale decision to be archived' in archived_file.read_text(encoding='utf-8')


def test_ingest_cycle_returns_archive_count_field(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Fresh decision', category='decision')

    report = ingest_cycle(tmp_path / '.memory')
    assert hasattr(report, 'archived_count')
    assert report.archived_count == 0
