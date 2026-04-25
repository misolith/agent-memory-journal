from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import re
from .bm25 import BM25Index
import os
import shutil
import tempfile
from datetime import datetime, timezone
from .storage import split_claim_and_metadata, extract_id, utc_now_iso, extract_state


@dataclass
class CoreRecallHit:
    text: str
    category: str
    path: str
    score: float
    line_no: int


def _update_last_seen(path_str: str, line_no: int):
    path = Path(path_str)
    if not path.exists():
        return
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    if line_no < 1 or line_no > len(lines):
        return
    line = lines[line_no - 1]
    if 'last_seen:' in line:
        new_line = re.sub(r'last_seen:[^\s\]]+', f'last_seen:{utc_now_iso()}', line)
    else:
        # Append last_seen before the closing bracket
        if line.endswith(']'):
            new_line = line[:-1] + f' last_seen:{utc_now_iso()}]'
        else:
            new_line = line + f' [last_seen:{utc_now_iso()}]'
    lines[line_no - 1] = new_line

    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines).rstrip() + '\n')
        shutil.move(temp_path, str(path))
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def recall_core(root: str | Path, query: str, k: int = 5, update_last_seen: bool = True) -> list[CoreRecallHit]:
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
    
    cache_path = root_path / 'index' / 'core_bm25.json'
    index = BM25Index.from_cache(cache_path, docs)
    scores = index.score(query)
    hits = [
        CoreRecallHit(text=doc, category=category, path=path, score=score, line_no=line_no)
        for doc, score, (category, path, line_no) in zip(docs, scores, meta)
        if score > 0
    ]
    hits.sort(key=lambda item: (-item.score, item.category, item.line_no))
    results = hits[:k]
    if update_last_seen:
        for hit in results:
            _update_last_seen(hit.path, hit.line_no)
    return results
