from pathlib import Path
import subprocess
import sys
import json

SCRIPT = Path(__file__).resolve().parents[1] / 'agent_memory_journal.py'


def run_cmd(tmp_path, *args, input_text=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )


def test_add_creates_long_file_when_missing(tmp_path):
    out = run_cmd(tmp_path, 'add', '--note', 'remember this forever', '--long')
    assert 'LONG_OK' in out.stdout
    assert (tmp_path / 'MEMORY.md').exists()


def test_extract_default_trigger_matches_remember(tmp_path):
    out = run_cmd(tmp_path, 'extract', input_text='hello\nremember this line\n')
    data = json.loads(out.stdout)
    assert 'remember this line' in data


def test_recent_json_empty(tmp_path):
    out = run_cmd(tmp_path, 'recent', '--days', '2', '--json')
    data = json.loads(out.stdout)
    assert data == []


def test_search_no_matches_contract(tmp_path):
    out = run_cmd(tmp_path, 'search', '--query', 'nothing')
    assert out.stdout.strip() == 'NO_MATCHES'


def test_candidates_pending_only_filters_existing_long_memory(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'from now on use app login for live tee times', '--long')
    run_cmd(tmp_path, 'add', '--note', 'remember to rotate the PAT before Friday')

    all_candidates = run_cmd(tmp_path, 'candidates', '--min-score', '1', '--json')
    all_data = json.loads(all_candidates.stdout)
    assert all_data['candidate_count'] >= 2
    assert any(item['already_in_long_memory'] for item in all_data['candidates'])

    pending = run_cmd(tmp_path, 'candidates', '--min-score', '1', '--pending-only', '--json')
    pending_data = json.loads(pending.stdout)
    assert pending_data['pending_only'] is True
    assert pending_data['candidate_count'] == 1
    assert all(not item['already_in_long_memory'] for item in pending_data['candidates'])
    assert 'rotate the pat' in pending_data['candidates'][0]['note'].lower()
