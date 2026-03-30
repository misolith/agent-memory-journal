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


def test_non_ascii_note_roundtrip(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'päätös säilyy muistissa')
    out = run_cmd(tmp_path, 'recent', '--days', '2')
    assert 'päätös säilyy muistissa' in out.stdout


def test_topic_matching_uses_tokens_not_substrings(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'pattern analysis only')
    run_cmd(tmp_path, 'add', '--note', 'remember this priority item for today')
    out = run_cmd(tmp_path, 'candidates', '--days', '7')
    assert 'remember this priority item for today' in out.stdout
