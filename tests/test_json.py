from pathlib import Path
import subprocess
import sys
import json

SCRIPT = Path(__file__).resolve().parents[1] / 'agent_memory_journal.py'


def run_cmd(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def test_recent_json(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir()
    (memory_dir / '2026-03-30.md').write_text('- 12:00 hello json\n', encoding='utf-8')
    out = run_cmd(tmp_path, 'recent', '--days', '2', '--json')
    data = json.loads(out.stdout)
    assert data[0]['note'] == 'hello json'


def test_candidates_json(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'remember from now on use app login for live tee times')
    out = run_cmd(tmp_path, 'candidates', '--days', '7', '--json')
    data = json.loads(out.stdout)
    assert 'candidates' in data
