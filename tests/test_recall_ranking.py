from __future__ import annotations

from collections import Counter
from pathlib import Path

from agent_memory import Journal
from agent_memory.bm25 import BM25Index
from agent_memory.normalize import normalize_claim


def test_normalize_claim_preserves_term_frequency():
    _canonical, tokens = normalize_claim('latency latency gateway gateway gateway')
    counter = Counter(tokens)
    # Repeated terms must survive normalisation so BM25 can use real TF.
    assert counter['gateway'] >= 2
    assert counter['latency'] >= 2


def test_bm25_score_rises_with_term_frequency():
    docs = ['gateway alert', 'gateway gateway gateway alert']
    index = BM25Index(docs)
    scores = index.score('gateway')
    assert scores[1] > scores[0]


def test_recall_all_prefers_warm_for_equivalent_match(tmp_path: Path):
    journal = Journal(root=tmp_path)
    journal.note('investigating gateway latency')
    journal.remember('gateway latency mitigation playbook', category='gotcha')

    hits = journal.recall('gateway latency', k=2, tier='all')
    assert hits, 'expected at least one hit'
    assert hits[0].tier == 'warm', [(h.tier, h.score, h.text) for h in hits]
