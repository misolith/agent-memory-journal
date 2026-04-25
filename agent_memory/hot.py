from __future__ import annotations

from pathlib import Path

from .storage import init_memory_root, extract_state

HOT_LIMIT_CHARS = 2048


def _has_metadata_flag(line: str, flag: str) -> bool:
    if '[' not in line or ']' not in line:
        return False
    meta = line.rsplit('[', 1)[-1].rstrip(']')
    return flag in meta.split()


def rebuild_agent_md(root: str | Path, max_chars: int = HOT_LIMIT_CHARS) -> dict[str, object]:
    paths = init_memory_root(root)
    selected: list[str] = []
    max_chars = min(max(256, int(paths.config.get('hot_max_chars', max_chars))), 10000)
    header = paths.config.get('hot_header', '# AGENT.md')

    for core_file in sorted(paths.core_dir.glob('*.md')):
        for line in core_file.read_text(encoding='utf-8', errors='ignore').splitlines():
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            if not _has_metadata_flag(stripped, 'pinned:true'):
                continue
            if extract_state(stripped) == 'superseded':
                continue
            selected.append(stripped)

    content_lines = [header, '']
    used = len('\n'.join(content_lines))
    kept: list[str] = []
    skipped: list[str] = []
    for item in selected:
        candidate = item
        addition = len(candidate) + 1
        if used + addition > max_chars:
            skipped.append(candidate)
            continue
        kept.append(candidate)
        used += addition

    if kept:
        content_lines.extend(kept)
    else:
        content_lines.append('')

    paths.hot_file.write_text('\n'.join(content_lines).rstrip() + '\n', encoding='utf-8')
    return {
        'written': len(kept),
        'skipped': len(skipped),
        'max_chars': max_chars,
        'path': str(paths.hot_file),
    }
