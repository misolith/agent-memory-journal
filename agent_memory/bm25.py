from __future__ import annotations

import math
from collections import Counter

from .normalize import normalize_claim


class BM25Index:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.doc_tokens = [normalize_claim(doc)[1] for doc in docs]
        self.doc_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_lens = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0
        self.idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        df = Counter()
        for tokens in self.doc_tokens:
            for token in set(tokens):
                df[token] += 1
        total = len(self.doc_tokens)
        return {
            token: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for token, freq in df.items()
        }

    def score(self, query: str) -> list[float]:
        q_tokens = normalize_claim(query)[1]
        scores: list[float] = []
        for freqs, doc_len in zip(self.doc_freqs, self.doc_lens):
            total = 0.0
            for token in q_tokens:
                if token not in freqs:
                    continue
                tf = freqs[token]
                idf = self.idf.get(token, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl if self.avgdl else 0.0))
                total += idf * ((tf * (self.k1 + 1)) / denom)
            scores.append(total)
        return scores
