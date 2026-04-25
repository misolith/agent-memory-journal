from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .hot import _has_metadata_flag
from .storage import init_memory_root


@dataclass
class DecayReport:
    archived: int
    retained: int
    archive_path: str


def archive_unpinned_core(root: str | Path, max_active_per_file: int = 50) -> DecayReport:
    paths = init_memory_root(root)
    archived = 0
    retained = 0

    for core_file in sorted(paths.core_dir.glob('*.md')):
        lines = core_file.read_text(encoding='utf-8', errors='ignore').splitlines()
        header = []
        bullets = []
        for line in lines:
            if line.strip().startswith('- '):
                bullets.append(line)
            else:
                header.append(line)

        pinned = [line for line in bullets if _has_metadata_flag(line, 'pinned:true')]
        unpinned = [line for line in bullets if not _has_metadata_flag(line, 'pinned:true')]
        keep_count = max(0, max_active_per_file - len(pinned))
        keep_unpinned = unpinned[-keep_count:] if keep_count else []
        move_unpinned = unpinned[:-keep_count] if keep_count else unpinned[:]

        if move_unpinned:
            archive_target = paths.archive_core_dir / core_file.name
            if not archive_target.exists():
                archive_target.write_text(f'# Archived {core_file.stem.title()}\n\n', encoding='utf-8')
            with archive_target.open('a', encoding='utf-8') as handle:
                for line in move_unpinned:
                    handle.write(line + '\n')
            archived += len(move_unpinned)

        new_lines = header[:]
        if new_lines and new_lines[-1] != '':
            new_lines.append('')
        new_lines.extend(pinned + keep_unpinned)
        core_file.write_text('\n'.join(new_lines).rstrip() + '\n', encoding='utf-8')
        retained += len(pinned) + len(keep_unpinned)

    return DecayReport(
        archived=archived,
        retained=retained,
        archive_path=str(paths.archive_core_dir),
    )
