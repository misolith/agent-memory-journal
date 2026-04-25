from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .normalize import token_counter


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
    query_tokens = token_counter(query)
    hits: list[CoreRecallHit] = []
    category_map = {
        'decisions': 'decision',
        'constraints': 'constraint',
        'gotchas': 'gotcha',
        'preferences': 'preference',
        'capabilities': 'capability',
    }
    for core_file in sorted(core_dir.glob('*.md')):
        category = category_map.get(core_file.stem, core_file.stem)
        for line_no, line in enumerate(core_file.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            line_tokens = token_counter(stripped)
            overlap = sum(min(line_tokens[token], query_tokens[token]) for token in query_tokens)
            substring_bonus = 1 if query.lower() in stripped.lower() else 0
            score = float(overlap + substring_bonus)
            if score <= 0:
                continue
            hits.append(CoreRecallHit(
                text=stripped[2:],
                category=category,
                path=str(core_file),
                score=score,
                line_no=line_no,
            ))
    hits.sort(key=lambda item: (-item.score, item.category, item.line_no))
    return hits[:k]
