from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .hot import effective_hot_budget
from .storage import init_memory_root


@dataclass
class DoctorReport:
    status: str
    hot_chars: int
    hot_over_limit: bool
    manifest_mismatches: list[str]
    checked_files: int


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def refresh_manifest(root: str | Path) -> dict[str, object]:
    paths = init_memory_root(root)
    tracked = {}
    for file_path in sorted(paths.core_dir.glob('*.md')):
        tracked[str(file_path.relative_to(paths.root))] = _hash_file(file_path)
    manifest = {
        'schema': 1,
        'layout': 'agent-memory-v2',
        'core_sha256': tracked,
    }
    target = paths.index_dir / 'manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


_DATE_RE = re.compile(r'(?:created|last_seen):([^\s\]]+)')


def _parse_entry_dates(text: str) -> list[date]:
    dates: list[date] = []
    for raw in _DATE_RE.findall(text):
        try:
            dates.append(datetime.fromisoformat(raw).date())
        except ValueError:
            continue
    return dates


def _file_matches_date_window(path: Path, after: date | None, before: date | None) -> bool:
    if after is None and before is None:
        return True
    entry_dates = _parse_entry_dates(path.read_text(encoding='utf-8', errors='ignore'))
    if not entry_dates:
        return False
    for entry_date in entry_dates:
        if after is not None and entry_date < after:
            continue
        if before is not None and entry_date > before:
            continue
        return True
    return False


def doctor_verify(root: str | Path, fix: bool = False, after: date | None = None, before: date | None = None) -> DoctorReport:
    paths = init_memory_root(root)
    manifest_path = paths.index_dir / 'manifest.json'
    if not manifest_path.exists() or fix:
        refresh_manifest(paths.root)

    mismatches: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception:
        manifest = {}
        mismatches.append('invalid:manifest-json')

    schema = manifest.get('schema')
    layout = manifest.get('layout')
    tracked = manifest.get('core_sha256')

    if schema != 1:
        mismatches.append('invalid:schema')
    if layout != 'agent-memory-v2':
        mismatches.append('invalid:layout')
    if not isinstance(tracked, dict) or not tracked:
        manifest = refresh_manifest(paths.root)
        tracked = manifest.get('core_sha256', {})

    checked = 0
    if not isinstance(tracked, dict):
        mismatches.append('invalid:core_sha256')
        tracked = {}

    for rel_path, expected in tracked.items():
        if not isinstance(rel_path, str) or not isinstance(expected, str):
            mismatches.append('invalid:core_sha256-entry')
            continue
        file_path = paths.root / rel_path
        if not file_path.exists():
            checked += 1
            mismatches.append(f'missing:{rel_path}')
            continue
        if not _file_matches_date_window(file_path, after=after, before=before):
            continue
        checked += 1
        actual = _hash_file(file_path)
        if actual != expected:
            mismatches.append(f'mismatch:{rel_path}')
    hot_chars = len(paths.hot_file.read_text(encoding='utf-8', errors='ignore')) if paths.hot_file.exists() else 0
    hot_budget = effective_hot_budget(paths.config)
    hot_over_limit = hot_chars > hot_budget
    status = 'OK' if not mismatches and not hot_over_limit and checked > 0 else 'ISSUES_FOUND'
    return DoctorReport(
        status=status,
        hot_chars=hot_chars,
        hot_over_limit=hot_over_limit,
        manifest_mismatches=mismatches,
        checked_files=checked,
    )
