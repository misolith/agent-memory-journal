from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

VALID_CATEGORIES = {"decision", "constraint", "gotcha", "preference", "capability"}


def sanitize_session_id(session_id: str) -> str:
    safe_session_id = ''.join(ch for ch in session_id if ch.isalnum() or ch in {'-', '_'})
    if not safe_session_id:
        raise ValueError('session_id must contain at least one safe character')
    return safe_session_id


@dataclass
class MemoryPaths:
    root: Path

    @property
    def hot_file(self) -> Path:
        return self.root / "AGENT.md"

    @property
    def episodic_dir(self) -> Path:
        return self.root / "episodic"

    @property
    def core_dir(self) -> Path:
        return self.root / "core"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    @property
    def archive_core_dir(self) -> Path:
        return self.root / "archive" / "core"

    @property
    def index_dir(self) -> Path:
        return self.root / "index"

    def core_file(self, category: str) -> Path:
        normalized = category.strip().lower()
        if normalized not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'")
        mapping = {
            "decision": "decisions.md",
            "constraint": "constraints.md",
            "gotcha": "gotchas.md",
            "preference": "preferences.md",
            "capability": "capabilities.md",
        }
        return self.core_dir / mapping[normalized]


def init_memory_root(root: str | Path) -> MemoryPaths:
    paths = MemoryPaths(Path(root).expanduser().resolve())
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.episodic_dir.mkdir(parents=True, exist_ok=True)
    paths.core_dir.mkdir(parents=True, exist_ok=True)
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.archive_core_dir.mkdir(parents=True, exist_ok=True)
    paths.index_dir.mkdir(parents=True, exist_ok=True)

    if not paths.hot_file.exists():
        paths.hot_file.write_text("# AGENT.md\n\n", encoding="utf-8")

    for category in sorted(VALID_CATEGORIES):
        target = paths.core_file(category)
        if not target.exists():
            title = target.stem.replace("_", " ").replace("-", " ").title()
            target.write_text(f"# {title}\n\n", encoding="utf-8")

    manifest = paths.index_dir / "manifest.json"
    if not manifest.exists():
        manifest.write_text('{"schema":1,"layout":"agent-memory-v2"}\n', encoding="utf-8")

    return paths


def append_episodic_note(root: str | Path, text: str, category: str | None = None, importance: str = "normal", source: str = "agent") -> Path:
    paths = init_memory_root(root)
    now = datetime.now()
    path = paths.episodic_dir / f"{now.date()}.md"
    suffix = []
    if category:
        suffix.append(f"category:{category}")
    if importance != "normal":
        suffix.append(f"importance:{importance}")
    if source:
        suffix.append(f"source:{source}")
    trailer = f" [{' '.join(suffix)}]" if suffix else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {now.strftime('%H:%M')} {text.strip()}{trailer}\n")
    return path


def append_core_memory(root: str | Path, category: str, text: str, source: str = "agent", pinned: bool = False) -> Path:
    paths = init_memory_root(root)
    target = paths.core_file(category)
    flags = [f"source:{source}"]
    if pinned:
        flags.append("pinned:true")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"- {text.strip()} [{' '.join(flags)}]\n")
    return target



def append_session_note(root: str | Path, session_id: str, text: str, category: str | None = None, importance: str = "normal", source: str = "agent") -> Path:
    paths = init_memory_root(root)
    safe_session_id = sanitize_session_id(session_id)
    target = paths.sessions_dir / f"{safe_session_id}.md"
    now = datetime.now()
    suffix = []
    if category:
        suffix.append(f"category:{category}")
    if importance != "normal":
        suffix.append(f"importance:{importance}")
    if source:
        suffix.append(f"source:{source}")
    trailer = f" [{' '.join(suffix)}]" if suffix else ""
    with target.open('a', encoding='utf-8') as handle:
        handle.write(f"- {now.strftime('%H:%M')} {text.strip()}{trailer}\n")
    return target
