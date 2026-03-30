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


def test_init_creates_layout_and_config(tmp_path):
    out = run_cmd(tmp_path, 'init', '--with-config')
    data = json.loads(out.stdout)
    assert (tmp_path / 'MEMORY.md').exists()
    assert (tmp_path / 'memory').exists()
    assert (tmp_path / 'agent-memory-journal.json').exists()
    assert str(tmp_path) == data['root']
