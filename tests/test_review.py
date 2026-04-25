from pathlib import Path

from agent_memory import Journal
from agent_memory.review import review_state


def test_review_state_reports_memory_layers(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.note_v2('Use v2 memory as development telemetry', category='decision', importance='high')
    episodic = tmp_path / '.memory' / 'episodic'
    episodic.mkdir(parents=True, exist_ok=True)
    (episodic / '2026-04-24.md').write_text('- 10:00 Use v2 memory as development telemetry [category:decision importance:high source:agent]\n', encoding='utf-8')
    journal.remember_v2('Pinned constraint for hot set', category='constraint', pinned=True)
    journal.session_note('s1', 'Shared session gotcha worth clustering', category='gotcha', importance='high')

    report = review_state(tmp_path / '.memory')
    hot_path = Path(report.hot_path)
    hot_text = hot_path.read_text(encoding='utf-8')

    assert report.episodic_candidates >= 1
    assert report.repeated_episodic_candidates >= 1
    assert report.session_candidates >= 1
    assert report.pinned_core_items == 1
    assert report.hot_chars > 0
    assert hot_path.exists()
    assert 'Pinned constraint for hot set' in hot_text


def test_review_state_reports_zero_pinned_core_items(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember_v2('Unpinned memory should stay out of hot set', category='decision', pinned=False)

    report = review_state(tmp_path / '.memory')

    assert report.pinned_core_items == 0


def test_review_state_ignores_pinned_text_outside_metadata(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.init_v2()
    core_file = tmp_path / '.memory' / 'core' / 'constraints.md'
    with core_file.open('a', encoding='utf-8') as handle:
        handle.write('- avoid literal pinned:true in docs [source:agent]\n')

    report = review_state(tmp_path / '.memory')
    hot_text = Path(report.hot_path).read_text(encoding='utf-8')

    assert report.pinned_core_items == 0
    assert 'avoid literal pinned:true in docs' not in hot_text
