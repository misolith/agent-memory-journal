#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import re
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/home/miso/.openclaw/workspace')
MEM_DIR = ROOT / 'memory'
LONG = ROOT / 'MEMORY.md'
LOCK_FILE = ROOT / '.memory_recall_guard.lock'

TRIGGERS = [
    r'\bmuista\b',
    r'\bremember\b',
    r'\bpäät(?:ös|ettiin)\b',
    r'\bfrom now on\b',
    r'\bjatkossa\b',
    r'\baina\b',
    r'\bprioriteetti\b',
]

LINE_RE = re.compile(r"^-\s+(\d{2}:\d{2})\s+(.*)$")
LONG_BULLET_RE = re.compile(r"^-\s+(.*)$")
DAILY_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


@contextmanager
def global_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open('a+', encoding='utf-8') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def today_daily_path() -> Path:
    return MEM_DIR / f"{datetime.now().date()}.md"


def normalize_note(note: str) -> str:
    """Normalize note text for stable duplicate checks."""
    text = note.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    return text


def is_recent_duplicate(note: str, window_minutes: int) -> bool:
    if window_minutes <= 0:
        return False

    target = normalize_note(note)
    now = datetime.now()

    # Check today's file and (when needed) yesterday's file so a late-night
    # note doesn't get duplicated right after midnight.
    files_with_date: list[tuple[Path, datetime.date]] = [(today_daily_path(), now.date())]
    if window_minutes > now.hour * 60 + now.minute:
        yday = now.date() - timedelta(days=1)
        files_with_date.append((MEM_DIR / f"{yday}.md", yday))

    for daily, file_date in files_with_date:
        if not daily.exists():
            continue

        try:
            lines = daily.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        # Scan from newest to oldest and stop once older than the dedupe window.
        for ln in reversed(lines):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, existing_note = m.group(1), m.group(2)
            try:
                ts = datetime.combine(file_date, datetime.strptime(hhmm, '%H:%M').time())
            except ValueError:
                continue

            age_min = (now - ts).total_seconds() / 60
            if age_min < 0:
                continue
            if age_min > window_minutes:
                break

            if normalize_note(existing_note) == target:
                return True

    return False


def has_long_duplicate(note: str) -> bool:
    if not LONG.exists():
        return False

    target = normalize_note(note)
    try:
        lines = LONG.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return False

    for ln in lines:
        m = LONG_BULLET_RE.match(ln.strip())
        if not m:
            continue
        if normalize_note(m.group(1)) == target:
            return True

    return False


def append_daily(note: str, dedupe_minutes: int = 0) -> bool:
    daily = today_daily_path()
    MEM_DIR.mkdir(parents=True, exist_ok=True)

    if is_recent_duplicate(note, dedupe_minutes):
        return False

    ts = datetime.now().strftime('%H:%M')
    with daily.open('a', encoding='utf-8') as f:
        f.write(f"- {ts} {note.strip()}\n")
    return True


def append_long(note: str, dedupe: bool = True) -> bool:
    if dedupe and has_long_duplicate(note):
        return False

    if not LONG.exists():
        LONG.write_text('# MEMORY.md\n\n', encoding='utf-8')
    with LONG.open('a', encoding='utf-8') as f:
        f.write(f"\n- {note.strip()}\n")
    return True


def extract_candidates(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        low = ln.lower()
        if any(re.search(t, low) for t in TRIGGERS):
            out.append(ln)
    return out


def iter_daily_files(
    days: int,
    after_date: datetime.date | None = None,
    before_date: datetime.date | None = None,
):
    if not MEM_DIR.exists():
        return []

    rolling_cutoff = datetime.now().date() - timedelta(days=max(0, days - 1))
    min_date = max(rolling_cutoff, after_date) if after_date else rolling_cutoff
    max_date = before_date
    candidates: list[tuple[datetime.date, Path]] = []

    for p in MEM_DIR.glob('*.md'):
        m = DAILY_FILE_RE.match(p.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), '%Y-%m-%d').date()
        except ValueError:
            continue
        if d < min_date:
            continue
        if max_date and d > max_date:
            continue
        candidates.append((d, p))

    return [p for _d, p in sorted(candidates, key=lambda x: x[0], reverse=True)]


def parse_iso_date(value: str) -> datetime.date:
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc


def collect_recent(days: int, limit: int, grep: str | None) -> list[dict[str, str]]:
    files = iter_daily_files(days)
    if not files:
        return []

    pattern = re.compile(grep, re.IGNORECASE) if grep else None
    out: list[dict[str, str]] = []

    for p in files:
        date = p.stem
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for ln in reversed(lines):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, note = m.group(1), m.group(2)
            if pattern and not pattern.search(note):
                continue

            out.append({'date': date, 'time': hhmm, 'note': note})
            if len(out) >= limit:
                return out

    return out


def print_recent(days: int, limit: int, grep: str | None, as_json: bool = False):
    items = collect_recent(days, limit, grep)

    if as_json:
        print(json.dumps(items, ensure_ascii=False))
        return

    files = iter_daily_files(days)
    if not files:
        print('NO_MEMORY_FILES')
        return

    if not items:
        print('NO_MATCHES')
        return

    for item in items:
        print(f"{item['date']} {item['time']} {item['note']}")


def search_notes(
    query: str,
    days: int,
    limit: int,
    regex: bool = False,
    source: str = 'all',
    after_date: datetime.date | None = None,
    before_date: datetime.date | None = None,
) -> list[dict[str, str]]:
    if regex:
        pattern = re.compile(query, re.IGNORECASE)
        matcher = lambda text: bool(pattern.search(text))
    else:
        needle = query.strip().lower()
        matcher = lambda text: needle in text.lower()

    out: list[dict[str, str]] = []

    include_long = source in {'all', 'long'}
    include_daily = source in {'all', 'daily'}

    if include_long and LONG.exists():
        try:
            long_lines = LONG.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            long_lines = []

        for i, ln in enumerate(long_lines, 1):
            m = LONG_BULLET_RE.match(ln.strip())
            if not m:
                continue
            note = m.group(1)
            if matcher(note):
                out.append({'source': 'long', 'ref': f'MEMORY.md:{i}', 'note': note})
                if len(out) >= limit:
                    return out

    if not include_daily:
        return out

    for p in iter_daily_files(days, after_date=after_date, before_date=before_date):
        date = p.stem
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for i, ln in enumerate(lines, 1):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, note = m.group(1), m.group(2)
            if not matcher(note):
                continue
            out.append({'source': 'daily', 'ref': f'{date}.md:{i}', 'time': hhmm, 'note': note})
            if len(out) >= limit:
                return out

    return out


def print_search(
    query: str,
    days: int,
    limit: int,
    regex: bool = False,
    as_json: bool = False,
    source: str = 'all',
    after_date: datetime.date | None = None,
    before_date: datetime.date | None = None,
):
    items = search_notes(
        query=query,
        days=days,
        limit=limit,
        regex=regex,
        source=source,
        after_date=after_date,
        before_date=before_date,
    )

    if as_json:
        print(json.dumps(items, ensure_ascii=False))
        return

    if not items:
        print('NO_MATCHES')
        return

    for item in items:
        if item['source'] == 'long':
            print(f"[long] {item['ref']} {item['note']}")
        else:
            print(f"[daily] {item['ref']} {item['time']} {item['note']}")


def _tokenize_words(text: str) -> list[str]:
    words = re.findall(r"[\wåäöÅÄÖ-]+", text.lower(), flags=re.UNICODE)
    stop = {
        'ja', 'on', 'the', 'a', 'an', 'to', 'of', 'for', 'in', 'with', 'että', 'kun', 'this', 'that',
        'from', 'was', 'are', 'is', 'be', 'by', 'or', 'as', 'at', 'it', 'we', 'you', 'i', 'my', 'our',
        'and', 'but', 'not', 'into', 'out', 'new', 'added', 'gained', 'now', 'also', 'recent', 'notes'
    }
    out = []
    for w in words:
        w = w.strip('-')
        if len(w) < 3 or w.isdigit() or w in stop:
            continue
        out.append(w)
    return out


def memory_stats(days: int = 7, top: int = 10) -> dict:
    files = iter_daily_files(days)
    note_count = 0
    days_with_notes = set()
    hourly = Counter()
    tokens = Counter()

    for p in files:
        date = p.stem
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for ln in lines:
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, note = m.group(1), m.group(2)
            note_count += 1
            days_with_notes.add(date)
            hourly[hhmm[:2]] += 1
            tokens.update(_tokenize_words(note))

    busiest_hours = [
        {'hour': hour, 'count': count}
        for hour, count in sorted(hourly.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, top)]
    ]
    top_words = [
        {'word': word, 'count': count}
        for word, count in tokens.most_common(max(1, top))
    ]

    return {
        'days_scanned': days,
        'files_found': len(files),
        'days_with_notes': len(days_with_notes),
        'note_count': note_count,
        'busiest_hours': busiest_hours,
        'top_words': top_words,
    }


def memory_topics(days: int = 14, top: int = 8, samples: int = 2, min_count: int = 2) -> dict:
    files = iter_daily_files(days)
    word_counts = Counter()
    word_samples: dict[str, list[dict[str, str]]] = {}
    note_count = 0

    for p in files:
        date = p.stem
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for i, ln in enumerate(lines, 1):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, note = m.group(1), m.group(2)
            note_count += 1
            seen = set(_tokenize_words(note))
            for word in seen:
                word_counts[word] += 1
                refs = word_samples.setdefault(word, [])
                if len(refs) < max(1, samples):
                    refs.append({'ref': f'{date}.md:{i}', 'time': hhmm, 'note': note})

    topics = []
    for word, count in word_counts.most_common():
        if count < max(1, min_count):
            continue
        topics.append({'word': word, 'count': count, 'samples': word_samples.get(word, [])})
        if len(topics) >= max(1, top):
            break

    return {
        'days_scanned': days,
        'files_found': len(files),
        'note_count': note_count,
        'min_count': max(1, min_count),
        'topics': topics,
    }


def print_stats(days: int = 7, top: int = 10, as_json: bool = False):
    stats = memory_stats(days=max(1, days), top=max(1, top))

    if as_json:
        print(json.dumps(stats, ensure_ascii=False))
        return

    print(
        f"days_scanned={stats['days_scanned']} files_found={stats['files_found']} "
        f"days_with_notes={stats['days_with_notes']} note_count={stats['note_count']}"
    )

    if stats['busiest_hours']:
        hours = ', '.join(f"{h['hour']}:00({h['count']})" for h in stats['busiest_hours'])
        print(f"busiest_hours: {hours}")
    else:
        print('busiest_hours: none')

    if stats['top_words']:
        words = ', '.join(f"{w['word']}({w['count']})" for w in stats['top_words'])
        print(f"top_words: {words}")
    else:
        print('top_words: none')


def print_topics(days: int = 14, top: int = 8, samples: int = 2, min_count: int = 2, as_json: bool = False):
    summary = memory_topics(days=max(1, days), top=max(1, top), samples=max(1, samples), min_count=max(1, min_count))

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    if not summary['topics']:
        print(
            f"days_scanned={summary['days_scanned']} files_found={summary['files_found']} "
            f"note_count={summary['note_count']} topics=0"
        )
        print('NO_TOPICS')
        return

    print(
        f"days_scanned={summary['days_scanned']} files_found={summary['files_found']} "
        f"note_count={summary['note_count']} topics={len(summary['topics'])}"
    )
    for topic in summary['topics']:
        print(f"topic {topic['word']} ({topic['count']})")
        for sample in topic['samples']:
            print(f"  - {sample['ref']} {sample['time']} {sample['note']}")


def memory_cadence(days: int = 14, top_hours: int = 3) -> dict:
    files = iter_daily_files(days)
    per_day: list[dict[str, object]] = []
    hourly_totals = Counter()
    total_notes = 0

    for p in reversed(files):
        date = p.stem
        day_count = 0
        hours = Counter()

        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for ln in lines:
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, _note = m.group(1), m.group(2)
            hour = hhmm[:2]
            day_count += 1
            total_notes += 1
            hours[hour] += 1
            hourly_totals[hour] += 1

        top_day_hours = [
            {'hour': hour, 'count': count}
            for hour, count in sorted(hours.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, top_hours)]
        ]
        per_day.append({'date': date, 'note_count': day_count, 'top_hours': top_day_hours})

    busiest_hours = [
        {'hour': hour, 'count': count}
        for hour, count in sorted(hourly_totals.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, top_hours)]
    ]

    return {
        'days_scanned': days,
        'files_found': len(files),
        'note_count': total_notes,
        'busiest_hours': busiest_hours,
        'per_day': per_day,
    }


def print_cadence(days: int = 14, top_hours: int = 3, as_json: bool = False):
    summary = memory_cadence(days=max(1, days), top_hours=max(1, top_hours))

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    print(
        f"days_scanned={summary['days_scanned']} files_found={summary['files_found']} "
        f"note_count={summary['note_count']}"
    )

    if summary['busiest_hours']:
        hours = ', '.join(f"{h['hour']}:00({h['count']})" for h in summary['busiest_hours'])
        print(f"busiest_hours: {hours}")
    else:
        print('busiest_hours: none')

    if not summary['per_day']:
        print('NO_MEMORY_FILES')
        return

    for day in summary['per_day']:
        day_hours = ', '.join(f"{h['hour']}:00({h['count']})" for h in day['top_hours']) if day['top_hours'] else 'none'
        print(f"{day['date']} notes={day['note_count']} top_hours={day_hours}")


def memory_digest(days: int = 7, recent_limit: int = 5, top: int = 5) -> dict:
    stats = memory_stats(days=max(1, days), top=max(1, top))
    cadence = memory_cadence(days=max(1, days), top_hours=max(1, min(top, 3)))
    topics = memory_topics(days=max(1, days), top=max(1, top), samples=1, min_count=2)
    recent = collect_recent(days=max(1, days), limit=max(1, recent_limit), grep=None)

    return {
        'days_scanned': max(1, days),
        'stats': stats,
        'cadence': cadence,
        'topics': topics,
        'recent': recent,
    }


def memory_candidates(days: int = 7, limit: int = 10, min_score: int = 2) -> dict:
    files = iter_daily_files(days=max(1, days))
    topic_words = {item['word'] for item in memory_topics(days=max(1, days), top=20, samples=1, min_count=2)['topics']}
    out: list[dict[str, object]] = []

    for p in files:
        date = p.stem
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        for i, ln in enumerate(reversed(lines), 1):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue

            hhmm, note = m.group(1), m.group(2)
            low = note.lower()
            reasons: list[str] = []
            score = 0

            triggered = [t for t in TRIGGERS if re.search(t, low)]
            if triggered:
                score += 2
                reasons.append('trigger_phrase')

            recurring = sorted(set(_tokenize_words(note)) & topic_words)
            if recurring:
                score += min(2, len(recurring))
                reasons.append(f"recurring_topic:{','.join(recurring[:3])}")

            if len(note) >= 90:
                score += 1
                reasons.append('substantial_note')

            if score < max(1, min_score):
                continue

            out.append({
                'ref': f'{date}.md:{len(lines) - i + 1}',
                'time': hhmm,
                'score': score,
                'reasons': reasons,
                'note': note,
            })

    out.sort(key=lambda item: (-int(item['score']), item['ref']), reverse=False)
    return {
        'days_scanned': max(1, days),
        'candidate_count': len(out),
        'candidates': out[: max(1, limit)],
    }


def print_digest(days: int = 7, recent_limit: int = 5, top: int = 5, as_json: bool = False):
    summary = memory_digest(days=max(1, days), recent_limit=max(1, recent_limit), top=max(1, top))

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    stats = summary['stats']
    cadence = summary['cadence']
    topics = summary['topics']
    recent = summary['recent']

    print(
        f"days_scanned={summary['days_scanned']} files_found={stats['files_found']} "
        f"days_with_notes={stats['days_with_notes']} note_count={stats['note_count']}"
    )

    busiest = cadence['busiest_hours']
    if busiest:
        hours = ', '.join(f"{h['hour']}:00({h['count']})" for h in busiest)
        print(f"busiest_hours: {hours}")
    else:
        print('busiest_hours: none')

    if topics['topics']:
        topic_line = ', '.join(f"{item['word']}({item['count']})" for item in topics['topics'])
        print(f"topics: {topic_line}")
    else:
        print('topics: none')

    if recent:
        print('recent_notes:')
        for item in recent:
            print(f"- {item['date']} {item['time']} {item['note']}")
    else:
        print('recent_notes: none')


def print_candidates(days: int = 7, limit: int = 10, min_score: int = 2, as_json: bool = False):
    summary = memory_candidates(days=max(1, days), limit=max(1, limit), min_score=max(1, min_score))

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    print(f"days_scanned={summary['days_scanned']} candidate_count={summary['candidate_count']}")
    if not summary['candidates']:
        print('NO_CANDIDATES')
        return

    for item in summary['candidates']:
        reasons = ', '.join(item['reasons']) if item['reasons'] else 'none'
        print(f"score={item['score']} {item['ref']} {item['time']} reasons={reasons}")
        print(f"  {item['note']}")


def main():
    ap = argparse.ArgumentParser(description='Memory recall helper')
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add')
    a.add_argument('--note', required=True)
    a.add_argument('--long', action='store_true', help='Also append to MEMORY.md')
    a.add_argument(
        '--dedupe-minutes',
        type=int,
        default=180,
        help='Skip writing if same note already exists within this many minutes (default: 180)',
    )
    a.add_argument(
        '--long-dedupe',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Skip appending to MEMORY.md when an equivalent bullet already exists (default: true)',
    )

    e = sub.add_parser('extract')
    e.add_argument('--file', required=True)

    r = sub.add_parser('recent', help='Show newest daily memory notes across recent days')
    r.add_argument('--days', type=int, default=2, help='How many recent days to scan (default: 2)')
    r.add_argument('--limit', type=int, default=15, help='Maximum notes to print (default: 15)')
    r.add_argument('--grep', help='Optional regex filter for note text (case-insensitive)')
    r.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    s = sub.add_parser('search', help='Search MEMORY.md + daily notes for text matches')
    s.add_argument('--query', required=True, help='Search text (literal by default)')
    s.add_argument('--days', type=int, default=30, help='How many recent daily files to scan (default: 30)')
    s.add_argument('--limit', type=int, default=20, help='Maximum matches to print (default: 20)')
    s.add_argument('--regex', action='store_true', help='Treat --query as a regex (case-insensitive)')
    s.add_argument('--source', choices=['all', 'long', 'daily'], default='all', help='Limit search scope (default: all)')
    s.add_argument('--after', type=parse_iso_date, help='Only include daily notes on/after YYYY-MM-DD')
    s.add_argument('--before', type=parse_iso_date, help='Only include daily notes on/before YYYY-MM-DD')
    s.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    st = sub.add_parser('stats', help='Summarize recent daily memory activity')
    st.add_argument('--days', type=int, default=7, help='How many recent days to scan (default: 7)')
    st.add_argument('--top', type=int, default=10, help='Top N busiest hours/words to print (default: 10)')
    st.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    tp = sub.add_parser('topics', help='Surface recurring note topics with sample references')
    tp.add_argument('--days', type=int, default=14, help='How many recent days to scan (default: 14)')
    tp.add_argument('--top', type=int, default=8, help='Maximum topic buckets to print (default: 8)')
    tp.add_argument('--samples', type=int, default=2, help='Sample notes to keep per topic (default: 2)')
    tp.add_argument('--min-count', type=int, default=2, help='Minimum number of notes a topic must appear in (default: 2)')
    tp.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    cd = sub.add_parser('cadence', help='Show daily note volume and busiest hours for recent memory activity')
    cd.add_argument('--days', type=int, default=14, help='How many recent days to scan (default: 14)')
    cd.add_argument('--top-hours', type=int, default=3, help='How many busiest hours to show overall/per day (default: 3)')
    cd.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    dg = sub.add_parser('digest', help='Print a compact operational digest of recent memory activity')
    dg.add_argument('--days', type=int, default=7, help='How many recent days to scan (default: 7)')
    dg.add_argument('--recent-limit', type=int, default=5, help='How many recent notes to include (default: 5)')
    dg.add_argument('--top', type=int, default=5, help='How many top topics/words to include (default: 5)')
    dg.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    cc = sub.add_parser('candidates', help='Surface likely long-term memory candidates from recent daily notes')
    cc.add_argument('--days', type=int, default=7, help='How many recent days to scan (default: 7)')
    cc.add_argument('--limit', type=int, default=10, help='Maximum candidates to print (default: 10)')
    cc.add_argument('--min-score', type=int, default=2, help='Minimum heuristic score required (default: 2)')
    cc.add_argument('--json', action='store_true', help='Emit structured JSON output for automation use')

    args = ap.parse_args()

    if args.cmd == 'add':
        with global_lock():
            added_daily = append_daily(args.note, dedupe_minutes=max(0, args.dedupe_minutes))
            long_status = None
            if args.long:
                added_long = append_long(args.note, dedupe=args.long_dedupe)
                long_status = 'LONG_OK' if added_long else 'LONG_SKIP_DUPLICATE'

        if long_status:
            daily_status = 'DAILY_OK' if added_daily else 'DAILY_SKIP_DUPLICATE'
            print(f'{daily_status} {long_status}')
        else:
            print('OK: note stored' if added_daily else 'SKIP_DUPLICATE: recent identical note exists')

    elif args.cmd == 'extract':
        text = Path(args.file).read_text(encoding='utf-8', errors='ignore')
        c = extract_candidates(text)
        if not c:
            print('NO_CANDIDATES')
        else:
            for i, ln in enumerate(c, 1):
                print(f'{i}. {ln}')

    elif args.cmd == 'recent':
        print_recent(days=max(1, args.days), limit=max(1, args.limit), grep=args.grep, as_json=args.json)

    elif args.cmd == 'search':
        if args.after and args.before and args.after > args.before:
            raise SystemExit("Invalid date range: --after cannot be later than --before")

        print_search(
            query=args.query,
            days=max(1, args.days),
            limit=max(1, args.limit),
            regex=args.regex,
            as_json=args.json,
            source=args.source,
            after_date=args.after,
            before_date=args.before,
        )

    elif args.cmd == 'stats':
        print_stats(days=max(1, args.days), top=max(1, args.top), as_json=args.json)

    elif args.cmd == 'topics':
        print_topics(
            days=max(1, args.days),
            top=max(1, args.top),
            samples=max(1, args.samples),
            min_count=max(1, args.min_count),
            as_json=args.json,
        )

    elif args.cmd == 'cadence':
        print_cadence(days=max(1, args.days), top_hours=max(1, args.top_hours), as_json=args.json)

    elif args.cmd == 'digest':
        print_digest(
            days=max(1, args.days),
            recent_limit=max(1, args.recent_limit),
            top=max(1, args.top),
            as_json=args.json,
        )

    elif args.cmd == 'candidates':
        print_candidates(
            days=max(1, args.days),
            limit=max(1, args.limit),
            min_score=max(1, args.min_score),
            as_json=args.json,
        )


if __name__ == '__main__':
    main()
