from agent_memory.bm25 import BM25Index


def test_bm25_scores_relevant_doc_higher():
    docs = [
        'supports browser control independently',
        'keep AGENT hot set tiny',
    ]
    index = BM25Index(docs)
    scores = index.score('browser control')
    assert scores[0] > scores[1]
