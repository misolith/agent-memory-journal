from pathlib import Path

from agent_memory import Journal
from agent_memory.normalize import claims_match, normalize_claim


def test_normalize_claim_reduces_surface_variation():
    normalized, tokens = normalize_claim('Now supports exact memory windows and reviewed promotions')
    assert 'support' in normalized or 'supports' in normalized
    assert 'memory' in tokens
    assert 'window' in normalized or 'windows' in normalized


def test_claims_match_handles_simple_paraphrase():
    a = 'Memory review now supports exact window filtering'
    b = 'Exact filtering windows are now supported for memory review'
    assert claims_match(a, b)


def test_journal_recall_matches_warm_v2_memory(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.remember('exact memory windows are now supported', category='capability')
    hits = journal.recall('supports exact memory window', k=3, tier='warm')
    assert hits
    assert 'exact memory windows are now supported' in hits[0].text
