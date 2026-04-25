from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bm25 import BM25Index
from .storage import split_claim_and_metadata


@dataclass
class CoreRecallHit:
    text: str
    category: str
    path: str
    score: float
    line_no: int


def recall_core(root: str | Path, query: str, k: int = 5) -> list[CoreRecallHit]:
    root_path = Path(root).expanduser().resolve()
    core_dir = root_path / 'core'
    if not query.strip():
        return []
    if k < 0:
        raise ValueError('k must be >= 0')
    if k == 0 or not core_dir.exists():
        return []
    category_map = {
        'decisions': 'decision',
        'constraints': 'constraint',
        'gotchas': 'gotcha',
        'preferences': 'preference',
        'capabilities': 'capability',
    }
    docs = []
    meta = []
    for core_file in sorted(core_dir.glob('*.md')):
        category = category_map.get(core_file.stem, core_file.stem)
        for line_no, line in enumerate(core_file.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            claim, _metadata = split_claim_and_metadata(stripped)
            docs.append(claim)
            meta.append((category, str(core_file), line_no))
    if not docs:
        return []
    index = BM25Index(docs)
    scores = index.score(query)
    hits = [
        CoreRecallHit(text=doc, category=category, path=path, score=score, line_no=line_no)
        for doc, score, (category, path, line_no) in zip(docs, scores, meta)
        if score > 0
    ]
    hits.sort(key=lambda item: (-item.score, item.category, item.line_no))
    return hits[:k]
