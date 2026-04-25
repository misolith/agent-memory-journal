from __future__ import annotations

import re

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
BLOCKLIST = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"^system:\s*", re.IGNORECASE),
    re.compile(r"^developer:\s*", re.IGNORECASE),
    re.compile(r"^assistant:\s*", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"reset\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"```(?:bash|sh|shell)?", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    cleaned = ZERO_WIDTH_RE.sub('', text)
    cleaned = CONTROL_RE.sub('', cleaned)
    return cleaned.strip()


def is_safe_memory_text(text: str) -> bool:
    cleaned = sanitize_text(text)
    if not cleaned:
        return False
    return not any(pattern.search(cleaned) for pattern in BLOCKLIST)


def require_safe_memory_text(text: str) -> str:
    cleaned = sanitize_text(text)
    if not is_safe_memory_text(cleaned):
        raise ValueError('unsafe memory text')
    return cleaned


def sanitize_evidence_text(text: str) -> str:
    cleaned = sanitize_text(text)
    if not cleaned:
        raise ValueError('empty memory text')
    return cleaned
