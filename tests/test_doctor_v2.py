from datetime import date
from pathlib import Path

from agent_memory import Journal
from agent_memory.doctor_v2 import doctor_verify, refresh_manifest


def test_refresh_manifest_tracks_core_hashes(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Pinned constraint for integrity', category='constraint', pinned=True)

    manifest = refresh_manifest(tmp_path / '.memory')

    assert 'core_sha256' in manifest
    assert 'core/constraints.md' in manifest['core_sha256']


def test_doctor_verify_detects_manifest_mismatch(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Stable core memory item', category='decision', pinned=True)
    refresh_manifest(tmp_path / '.memory')

    decisions = tmp_path / '.memory' / 'core' / 'decisions.md'
    with decisions.open('a', encoding='utf-8') as handle:
        handle.write('- tampered after manifest [source:agent]\n')

    report = doctor_verify(tmp_path / '.memory')

    assert report.status == 'ISSUES_FOUND'
    assert any(item.startswith('mismatch:core/decisions.md') for item in report.manifest_mismatches)


def test_doctor_verify_checks_hot_limit(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init()
    hot_file = tmp_path / '.memory' / 'AGENT.md'
    hot_file.write_text('# AGENT.md\n\n' + ('x' * 3000), encoding='utf-8')
    refresh_manifest(tmp_path / '.memory')

    report = doctor_verify(tmp_path / '.memory')

    assert report.hot_over_limit is True
    assert report.status == 'ISSUES_FOUND'


def test_doctor_verify_refreshes_empty_manifest_tracking(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Core item should be verified on first doctor run', category='capability', pinned=True)

    report = doctor_verify(tmp_path / '.memory')

    assert report.checked_files > 0
    assert report.status == 'OK'


def test_doctor_verify_flags_invalid_manifest_shape(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('Core item for malformed manifest test', category='decision', pinned=True)
    manifest = tmp_path / '.memory' / 'index' / 'manifest.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"schema": 2, "layout": "broken", "core_sha256": []}\n', encoding='utf-8')

    report = doctor_verify(tmp_path / '.memory')

    assert report.status == 'ISSUES_FOUND'
    assert 'invalid:schema' in report.manifest_mismatches
    assert 'invalid:layout' in report.manifest_mismatches


def test_doctor_verify_can_scope_checks_by_date_window(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init()
    decisions = tmp_path / '.memory' / 'core' / 'decisions.md'
    constraints = tmp_path / '.memory' / 'core' / 'constraints.md'
    decisions.write_text(
        '# Decisions\n\n- Old decision [id:dec-old state:active source:agent created:2026-04-20T10:00:00+00:00 last_seen:2026-04-20T10:00:00+00:00]\n',
        encoding='utf-8',
    )
    constraints.write_text(
        '# Constraints\n\n- New constraint [id:con-new state:active source:agent created:2026-04-29T10:00:00+00:00 last_seen:2026-04-29T10:00:00+00:00]\n',
        encoding='utf-8',
    )
    refresh_manifest(tmp_path / '.memory')

    with decisions.open('a', encoding='utf-8') as handle:
        handle.write('- tampered after manifest [source:agent]\n')

    scoped = doctor_verify(tmp_path / '.memory', after=date(2026, 4, 25))
    full = doctor_verify(tmp_path / '.memory')

    assert scoped.status == 'OK'
    assert scoped.checked_files == 1
    assert full.status == 'ISSUES_FOUND'
    assert any(item.startswith('mismatch:core/decisions.md') for item in full.manifest_mismatches)
