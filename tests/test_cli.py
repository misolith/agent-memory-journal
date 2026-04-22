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


def test_review_shows_related_long_memory(tmp_path):
    run_cmd(tmp_path, 'add', '--note', 'memory recall guard now supports review mode for candidate promotion', '--long')
    run_cmd(tmp_path, 'add', '--note', 'memory recall guard now supports review mode for candidate promotion with promote commands')
    out = run_cmd(tmp_path, 'review', '--days', '2', '--limit', '5', '--min-score', '2')
    assert 'related_long_matches:' in out.stdout
    assert 'promote:' in out.stdout
    assert 'reason_counts:' in out.stdout
    assert 'batch_promote:' in out.stdout
    assert 'promote-candidates' in out.stdout


def test_candidates_and_review_support_exact_date_filters(tmp_path):
    mem = tmp_path / 'memory'
    mem.mkdir(parents=True, exist_ok=True)
    (mem / '2026-04-10.md').write_text('- 08:00 remember earlier policy\n', encoding='utf-8')
    (mem / '2026-04-11.md').write_text('- 09:00 remember scoped policy shift\n', encoding='utf-8')

    candidates = run_cmd(
        tmp_path,
        'candidates',
        '--days', '30',
        '--min-score', '1',
        '--after', '2026-04-11',
        '--before', '2026-04-11',
    )
    assert '2026-04-11.md:1' in candidates.stdout
    assert '2026-04-10.md:1' not in candidates.stdout

    review = run_cmd(
        tmp_path,
        'review',
        '--days', '30',
        '--min-score', '1',
        '--after', '2026-04-11',
        '--before', '2026-04-11',
    )
    assert '--after 2026-04-11 --before 2026-04-11' in review.stdout
    assert '2026-04-11.md:1' in review.stdout
    assert '2026-04-10.md:1' not in review.stdout


def test_doctor_reports_duplicate_long_memory_and_bad_daily_lines(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / 'MEMORY.md').write_text(
        '# MEMORY.md\n\n- repeated durable note\n- Repeated durable note\n',
        encoding='utf-8',
    )
    (memory_dir / '2026-04-20.md').write_text(
        '- 09:00 first note\n- malformed bullet\n- 08:30 out of order\n',
        encoding='utf-8',
    )

    out = run_cmd(tmp_path, 'doctor', '--days', '30')
    assert 'status=ISSUES_FOUND' in out.stdout
    assert 'long_duplicates:' in out.stdout
    assert 'malformed_daily_lines:' in out.stdout
    assert 'daily_timestamp_order_issues:' in out.stdout


def test_doctor_strict_exits_nonzero_when_issues_exist(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / '2026-04-20.md').write_text('- malformed bullet\n', encoding='utf-8')

    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), 'doctor', '--days', '30', '--strict'],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert 'status=ISSUES_FOUND' in result.stdout


def test_doctor_strict_stays_zero_when_clean(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / '2026-04-20.md').write_text('- 09:00 all clear\n', encoding='utf-8')

    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--root', str(tmp_path), 'doctor', '--days', '30', '--strict'],
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'status=OK' in result.stdout


def test_doctor_supports_exact_date_filters(tmp_path):
    memory_dir = tmp_path / 'memory'
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / '2026-04-10.md').write_text('- malformed old bullet\n', encoding='utf-8')
    (memory_dir / '2026-04-11.md').write_text('- malformed target bullet\n', encoding='utf-8')

    out = run_cmd(
        tmp_path,
        'doctor',
        '--days', '30',
        '--after', '2026-04-11',
        '--before', '2026-04-11',
    )
    assert '2026-04-11.md:1' in out.stdout
    assert '2026-04-10.md:1' not in out.stdout


def test_doctor_rejects_inverted_date_range(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            '--root',
            str(tmp_path),
            'doctor',
            '--after',
            '2026-04-12',
            '--before',
            '2026-04-11',
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'Invalid date range' in result.stderr or 'Invalid date range' in result.stdout
