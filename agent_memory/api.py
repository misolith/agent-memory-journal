from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .core_recall import recall_core
from .episodic_recall import recall_episodic
from .ingest import ingest_cycle
from .models import RecallResult
from .normalize import token_counter
from .review_memory import log_review_findings
from .storage import append_core_memory, append_episodic_note, append_session_note, init_memory_root, supersede_memory


class LegacyJournal:
    def __init__(self, root: str | Path = '.'):
        self.root = Path(root).expanduser().resolve()
        self.long_file = self.root / 'MEMORY.md'
        self.daily_dir = self.root / 'memory'

    def recall(self, query: str, k: int = 5, tier: str = 'all') -> list[RecallResult]:
        q = query.lower().strip()
        results: list[RecallResult] = []
        if tier in {'all', 'warm'} and self.long_file.exists():
            results.extend(self._scan_file(self.long_file, q, tier='warm'))
        if tier in {'all', 'cold'} and self.daily_dir.exists():
            for path in sorted(self.daily_dir.glob('*.md'), reverse=True):
                results.extend(self._scan_file(path, q, tier='cold'))
        results.sort(key=lambda item: (-item.score, item.path, item.line_no))
        return results[: max(1, k)]

    def note(self, text: str, category: str | None = None, importance: str = 'normal', source: str = 'agent') -> Path:
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        path = self.daily_dir / f"{datetime.now().date()}.md"
        ts = datetime.now().strftime('%H:%M')
        suffix = ''
        if category:
            suffix += f' [category:{category}]'
        if importance != 'normal':
            suffix += f' [importance:{importance}]'
        with path.open('a', encoding='utf-8') as handle:
            handle.write(f"- {ts} {text.strip()}{suffix}\n")
        return path

    def _scan_file(self, path: Path, query: str, tier: str) -> Iterable[RecallResult]:
        for line_no, line in enumerate(path.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
            lowered = line.lower()
            if not query:
                continue
            query_tokens = token_counter(query)
            line_tokens = token_counter(line)
            overlap = sum(min(line_tokens[t], query_tokens[t]) for t in query_tokens)
            substring_bonus = 1 if query in lowered else 0
            if overlap or substring_bonus:
                score = float(overlap + substring_bonus)
                yield RecallResult(text=line.strip(), path=str(path), line_no=line_no, score=score, tier=tier)


class Journal:
    def __init__(self, root: str | Path = '.'):
        self.root = Path(root).expanduser().resolve()
        self.v2_root = self.root if self.root.name == '.memory' else self.root / '.memory'

    def init(self) -> Path:
        return init_memory_root(self.v2_root).root

    def recall(self, query: str, k: int = 5, tier: str = 'all'):
        if tier == 'warm':
            return self.recall_core(query, k=k)
        if tier == 'cold':
            return recall_episodic(self.v2_root, query=query, k=k)
        if tier == 'all':
            warm_hits = self.recall_core(query, k=max(1, k))
            # Weight warm hits higher (e.g. 1.5x)
            for h in warm_hits:
                h.score *= 1.5
                h.tier = 'warm'

            cold_hits = recall_episodic(self.v2_root, query=query, k=max(1, k))
            for h in cold_hits:
                h.tier = 'cold'

            merged = list(warm_hits) + list(cold_hits)
            merged.sort(key=lambda item: (-item.score, getattr(item, 'path', ''), getattr(item, 'line_no', 0)))
            return merged[: max(1, k)]
        return []

    def note(self, text: str, category: str | None = None, importance: str = 'normal', source: str = 'agent') -> Path:
        return append_episodic_note(self.v2_root, text=text, category=category, importance=importance, source=source)

    def remember(self, text: str, category: str, source: str = 'agent', pinned: bool = False, supersedes: str | None = None) -> Path:
        return append_core_memory(self.v2_root, category=category, text=text, source=source, pinned=pinned, supersedes=supersedes)

    def forget(self, memory_id: str) -> bool:
        return supersede_memory(self.v2_root, memory_id=memory_id)

    def session_note(self, session_id: str, text: str, category: str | None = None, importance: str = 'normal', source: str = 'agent') -> Path:
        return append_session_note(self.v2_root, session_id=session_id, text=text, category=category, importance=importance, source=source)

    def recall_core(self, query: str, k: int = 5):
        return recall_core(self.v2_root, query=query, k=k)

    def ingest(self):
        return ingest_cycle(self.v2_root)

    def log_review_findings(self, session_id: str, findings: list[str], category: str = 'gotcha'):
        return log_review_findings(self.v2_root, session_id=session_id, findings=findings, category=category)
