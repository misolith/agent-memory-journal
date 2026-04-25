from agent_memory import Journal
from agent_memory.episodic_recall import recall_episodic


def test_recall_episodic_finds_v2_daily_notes(tmp_path):
    journal = Journal(root=tmp_path)
    journal.note('Decision: keep AGENT hot set tiny', category='decision', importance='high')

    hits = recall_episodic(tmp_path / '.memory', 'hot set tiny', k=5)

    assert hits
    assert 'hot set tiny' in hits[0].text.lower()
