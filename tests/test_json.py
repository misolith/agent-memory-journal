from datetime import date, timedelta
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
    today = date.today().isoformat()
    (memory_dir / f'{today}.md').write_text('- 12:00 hello json\n', encoding='utf-8')
    out = run_cmd(tmp_path, 'recent', '--days', '2', '--json')
    data = json.loads(out.stdout)
    assert data[0]['note'] == 'hello json'


def test_recent_json_date_range_filters(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir()
    base = date.today()
    early = (base - timedelta(days=1)).isoformat()
    included = base.isoformat()
    late = (base + timedelta(days=1)).isoformat()
    (memory_dir / f'{early}.md').write_text('- 10:00 too early\n', encoding='utf-8')
    (memory_dir / f'{included}.md').write_text('- 12:00 included\n', encoding='utf-8')
    (memory_dir / f'{late}.md').write_text('- 14:00 too late\n', encoding='utf-8')

    out = run_cmd(
        tmp_path,
        'recent',
        '--days', '10',
        '--after', included,
        '--before', included,
        '--json',
    )
    data = json.loads(out.stdout)
    assert [item['note'] for item in data] == ['included']


def test_candidates_json(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'remember from now on use app login for live tee times')
    out = run_cmd(tmp_path, 'candidates', '--days', '7', '--json')
    data = json.loads(out.stdout)
    assert 'candidates' in data


def test_promote_command_by_ref(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir()
    today = date.today().isoformat()
    (memory_dir / f'{today}.md').write_text('- 12:00 durable note\n', encoding='utf-8')

    out = run_cmd(tmp_path, 'promote', '--ref', f'{today}.md:1', '--prefix-date')
    assert 'LONG_OK' in out.stdout

    long_text = (tmp_path / 'MEMORY.md').read_text(encoding='utf-8')
    assert f'- {today}: durable note' in long_text


def test_promote_candidates_json_dry_run(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'remember from now on route degraded workflows with evidence receipts')
    out = run_cmd(tmp_path, 'promote-candidates', '--days', '7', '--dry-run', '--json')
    data = json.loads(out.stdout)
    assert data['requested'] == 1
    assert data['added'] == 0
    assert data['results'][0]['status'] == 'DRY_RUN'
