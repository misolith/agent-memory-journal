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


def test_extract_uses_custom_trigger_config(tmp_path):
    config = {"triggers": [r"\bwisegolf\b"]}
    (tmp_path / 'agent-memory-journal.json').write_text(json.dumps(config), encoding='utf-8')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), 'extract'],
        input='nothing here\nwisegolf booking flow\n',
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'wisegolf booking flow' in result.stdout
