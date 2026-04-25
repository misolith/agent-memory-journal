from pathlib import Path

from agent_memory.review_memory import log_review_findings


def test_log_review_findings_writes_session_notes(tmp_path: Path):
    report = log_review_findings(
        root=tmp_path,
        session_id='review-1',
        findings=['Pinned detection is too loose', 'Thresholds are duplicated'],
    )

    target = tmp_path / '.memory' / 'sessions' / 'review-1.md'
    content = target.read_text(encoding='utf-8')

    assert report.notes_written == 2
    assert report.session_candidates == 2
    assert report.session_id == 'review-1'
    assert 'Pinned detection is too loose' in content


def test_log_review_findings_accumulates_cross_session_candidates(tmp_path: Path):
    log_review_findings(tmp_path, 'review-a', ['Pinned detection is too loose'])
    report = log_review_findings(tmp_path, 'review-b', ['Pinned detection remains too loose'])

    assert report.session_candidates == 1


def test_log_review_findings_returns_sanitized_session_id_and_skips_blanks(tmp_path: Path):
    report = log_review_findings(tmp_path, 'review/bad', ['  ', 'Actual finding', ''])
    target = tmp_path / '.memory' / 'sessions' / 'reviewbad.md'
    content = target.read_text(encoding='utf-8')

    assert report.session_id == 'reviewbad'
    assert report.notes_written == 1
    assert 'Actual finding' in content
