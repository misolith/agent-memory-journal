from agent_memory import Journal
from agent_memory.core_recall import recall_core
from agent_memory.examples import render_examples
from agent_memory.ingest import ingest_cycle


def test_render_examples_contains_v2_flows():
    rendered = render_examples()

    assert 'note_v2' in rendered
    assert 'remember_v2' in rendered
    assert 'session_note' in rendered
    assert 'recall_core' in rendered
    assert 'ingest_cycle' in rendered


def test_v2_example_flow_executes(tmp_path):
    journal = Journal(root=tmp_path)
    v2_root = journal.init_v2()
    note_path = journal.note_v2('Decision: keep AGENT hot set tiny', category='decision', importance='high')
    core_path = journal.remember_v2('AGENT.md must stay small and pinned-only', category='constraint', pinned=True)
    session_path = journal.session_note('review-42', 'Pinned detection is too loose', category='gotcha', importance='high')

    hits = recall_core(v2_root, 'pinned-only', k=5)
    report = ingest_cycle(v2_root)

    assert note_path.exists()
    assert core_path.exists()
    assert session_path.exists()
    assert hits
    assert report.hot_written >= 1
    assert report.review_hot_chars > 0
