from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from agent_memory.cli import main


def _run(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, 'argv', ['agent-memory-journal', *args])
    main()


def test_cli_init_creates_layout(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _run(monkeypatch, ['--root', str(tmp_path), 'init'])
    capsys.readouterr()
    memory = tmp_path / '.memory'
    assert (memory / 'AGENT.md').exists()
    assert (memory / 'config.json').exists()
    for sub in ('core', 'episodic', 'sessions', 'index', 'archive'):
        assert (memory / sub).is_dir()


def test_cli_digest_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _run(monkeypatch, ['--root', str(tmp_path), 'init'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'note', 'Investigating gateway latency'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'digest'])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload['days_scanned'] == 7
    assert 'recent' in payload
    assert isinstance(payload['recent'], list)


def test_cli_recent_without_grep_returns_recent_notes(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _run(monkeypatch, ['--root', str(tmp_path), 'init'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'note', 'Today\'s observation'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'recent', '--days', '7', '--json'])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert any('observation' in hit['text'] for hit in payload), payload


def test_cli_doctor_stays_ok_after_remember(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _run(monkeypatch, ['--root', str(tmp_path), 'init'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'remember', 'Pinned rule', '--category', 'constraint', '--pinned'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'doctor', '--json'])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload['status'] == 'OK', payload


def test_cli_doctor_stays_ok_after_forget(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    import re

    _run(monkeypatch, ['--root', str(tmp_path), 'init'])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'remember', 'Older policy', '--category', 'decision'])
    capsys.readouterr()
    decisions = (tmp_path / '.memory' / 'core' / 'decisions.md').read_text(encoding='utf-8')
    match = re.search(r'id:([^\s\]]+)', decisions)
    assert match, decisions
    _run(monkeypatch, ['--root', str(tmp_path), 'forget', match.group(1)])
    capsys.readouterr()
    _run(monkeypatch, ['--root', str(tmp_path), 'doctor', '--json'])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload['status'] == 'OK', payload
