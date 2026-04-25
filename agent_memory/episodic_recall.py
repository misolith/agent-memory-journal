from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bm25 import BM25Index


@dataclass
class EpisodicRecallHit:
    text: str
    path: str
    score: float
    line_no: int


def recall_episodic(root: str | Path, query: str, k: int = 5) -> list[EpisodicRecallHit]:
    root_path = Path(root).expanduser().resolve()
    episodic_dir = root_path / 'episodic'
    if not query.strip():
        return []
    if k < 0:
        raise ValueError('k must be >= 0')
    if k == 0 or not episodic_dir.exists():
        return []
    docs = []
    meta = []
    for daily_file in sorted(episodic_dir.glob('*.md')):
        for line_no, line in enumerate(daily_file.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            docs.append(stripped[2:])
            meta.append((str(daily_file), line_no))
    if not docs:
        return []
    index = BM25Index(docs)
    scores = index.score(query)
    hits = [
        EpisodicRecallHit(text=doc, path=path, score=score, line_no=line_no)
        for doc, score, (path, line_no) in zip(docs, scores, meta)
        if score > 0
    ]
    hits.sort(key=lambda item: (-item.score, item.path, item.line_no))
    return hits[:k]
