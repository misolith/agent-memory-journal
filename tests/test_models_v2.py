from agent_memory.models_v2 import CandidateItem, MemoryItem


def test_memory_item_defaults_are_stable():
    item = MemoryItem(
        id='mem-1',
        text='Keep AGENT.md tiny',
        category='constraint',
        tier='warm',
        state='active',
        source='agent',
    )

    assert item.pinned is False
    assert item.supersedes is None


def test_candidate_item_captures_promotion_fields():
    candidate = CandidateItem(
        id='cand-1',
        text='Pinned detection is too loose',
        normalized_claim='detection loose pinned',
        category='gotcha',
        source='subagent',
        occurrences=2,
        distinct_days=2,
        score=5.0,
    )

    assert candidate.category == 'gotcha'
    assert candidate.occurrences == 2
    assert candidate.score == 5.0
