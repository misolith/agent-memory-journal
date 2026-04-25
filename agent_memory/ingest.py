from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .hot import rebuild_agent_md
from .promote import promote_repeated_candidates
from .review import review_state
from .storage import init_memory_root


@dataclass
class IngestReport:
    promoted_count: int
    hot_written: int
    hot_skipped: int
    review_status: str
    review_hot_chars: int


def ingest_cycle(root: str | Path) -> IngestReport:
    paths = init_memory_root(root)
    promoted = promote_repeated_candidates(paths.root)
    hot = rebuild_agent_md(paths.root)
    review = review_state(paths.root)
    return IngestReport(
        promoted_count=len(promoted),
        hot_written=int(hot['written']),
        hot_skipped=int(hot['skipped']),
        review_status=review.status,
        review_hot_chars=review.hot_chars,
    )
