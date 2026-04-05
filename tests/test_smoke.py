from datetime import date
from pathlib import Path
import subprocess
import sys


def test_repo_has_core_files():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'agent_memory_journal.py').exists()
    assert (root / 'README.md').exists()
    assert (root / 'pyproject.toml').exists()


def test_recent_command_works_in_temp_root(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'agent_memory_journal.py'
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir()
    today = date.today().isoformat()
    (memory_dir / f'{today}.md').write_text('- 12:00 hello world\n', encoding='utf-8')
    result = subprocess.run(
        [sys.executable, str(script), '--root', str(tmp_path), 'recent', '--days', '2'],
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'hello world' in result.stdout
