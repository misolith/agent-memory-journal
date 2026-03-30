from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'agent_memory_journal.py'


def test_help_contains_examples():
    result = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True, check=True)
    assert 'Examples:' in result.stdout
    assert '--root /workspace recent --days 2' in result.stdout


def test_version_flag():
    result = subprocess.run([sys.executable, str(SCRIPT), '--version'], capture_output=True, text=True, check=True)
    assert '0.1.0' in result.stdout
