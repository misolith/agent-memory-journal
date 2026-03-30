from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'agent_memory_journal.py'


def run_cmd(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def test_add_and_recent(tmp_path):
    out = run_cmd(tmp_path, 'add', '--note', 'remember this')
    assert 'OK: note stored' in out.stdout
    recent = run_cmd(tmp_path, 'recent', '--days', '2')
    assert 'remember this' in recent.stdout


def test_long_memory_dedupe(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'from now on use app login', '--long')
    out = run_cmd(tmp_path, 'add', '--note', 'from now on use app login', '--long')
    assert 'LONG_SKIP_DUPLICATE' in out.stdout


def test_search_and_digest(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'golf booking flow uses wisegolf app')
    run_cmd(tmp_path, 'add', '--note', 'remember pat rotation before friday')
    search = run_cmd(tmp_path, 'search', '--query', 'wisegolf')
    assert 'wisegolf' in search.stdout.lower()
    digest = run_cmd(tmp_path, 'digest', '--days', '7')
    assert 'recent_notes:' in digest.stdout
