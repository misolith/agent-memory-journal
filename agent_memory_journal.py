#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

VERSION = '0.1.2'

LINE_RE = re.compile(r"^-\s+(\d{2}:\d{2})\s+(.*)$")
LONG_BULLET_RE = re.compile(r"^-\s+(.*)$")
DAILY_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
DAILY_REF_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md:(\d+)$")


class JournalPaths:
    def __init__(self, root: Path, memory_dir: str = 'memory', long_file: str = 'MEMORY.md'):
        self.root = root
        self.mem_dir = root / memory_dir
        self.long = root / long_file
        self.lock_file = root / '.agent_memory_journal.lock'

    def today_daily_path(self) -> Path:
        return self.mem_dir / f"{datetime.now().date()}.md"


def default_root() -> Path:
    env = os.environ.get('AGENT_MEMORY_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd()


def default_triggers():
    return [
        r'\bremember\b',
        r'\bdecision\b',
        r'\bdecided\b',
        r'\bfrom now on\b',
        r'\balways\b',
        r'\bpriority\b',
    ]


def load_config(paths: "JournalPaths", config_file: str | None = None) -> dict:
    if config_file:
        candidate = Path(config_file).expanduser()
        if not candidate.is_absolute():
            candidate = paths.root / candidate
    else:
        candidate = paths.root / 'agent-memory-journal.json'
    if not candidate.exists():
        return {'triggers': default_triggers(), 'config_path': None}
    data = json.loads(candidate.read_text(encoding='utf-8'))
    triggers = data.get('triggers') or default_triggers()
    return {'triggers': triggers, 'config_path': str(candidate)}


@contextmanager
def global_lock(paths: JournalPaths):
    paths.root.mkdir(parents=True, exist_ok=True)
    with paths.lock_file.open('a+', encoding='utf-8') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def normalize_note(note: str) -> str:
    text = note.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    return text


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-zÅÄÖåäö0-9-]{3,}", text)]


def is_recent_duplicate(paths: JournalPaths, note: str, window_minutes: int) -> bool:
    if window_minutes <= 0:
        return False

    target = normalize_note(note)
    now = datetime.now()
    files_with_date: list[tuple[Path, datetime.date]] = [(paths.today_daily_path(), now.date())]
    if window_minutes > now.hour * 60 + now.minute:
        yday = now.date() - timedelta(days=1)
        files_with_date.append((paths.mem_dir / f"{yday}.md", yday))

    for daily, file_date in files_with_date:
        if not daily.exists():
            continue
        try:
            lines = daily.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
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


def has_long_duplicate(paths: JournalPaths, note: str) -> bool:
    if not paths.long.exists():
        return False
    target = normalize_note(note)
    try:
        lines = paths.long.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return False
    for ln in lines:
        m = LONG_BULLET_RE.match(ln.strip())
        if not m:
            continue
        if normalize_note(m.group(1)) == target:
            return True
    return False


def long_memory_duplicates(paths: JournalPaths) -> list[dict[str, object]]:
    if not paths.long.exists():
        return []
    seen: dict[str, dict[str, object]] = {}
    try:
        lines = paths.long.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return []
    for line_no, raw in enumerate(lines, start=1):
        m = LONG_BULLET_RE.match(raw.strip())
        if not m:
            continue
        note = m.group(1).strip()
        normalized = normalize_note(note)
        if not normalized:
            continue
        bucket = seen.setdefault(normalized, {'note': note, 'count': 0, 'lines': []})
        bucket['count'] += 1
        bucket['lines'].append(line_no)
    return sorted(
        [item for item in seen.values() if item['count'] > 1],
        key=lambda item: (-int(item['count']), item['note'].lower()),
    )


def daily_file_health(path: Path) -> dict[str, object]:
    malformed: list[dict[str, object]] = []
    timestamp_order_issues: list[dict[str, object]] = []

    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception as exc:
        return {
            'path': str(path),
            'malformed': [{'line_no': 0, 'text': f'READ_ERROR: {exc}'}],
            'timestamp_order_issues': [],
        }

    previous_minutes: int | None = None
    previous_time: str | None = None
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped.startswith('- '):
            continue

        match = LINE_RE.match(stripped)
        if not match:
            malformed.append({'line_no': line_no, 'text': raw})
            continue

        hhmm = match.group(1)
        try:
            parsed = datetime.strptime(hhmm, '%H:%M').time()
        except ValueError:
            malformed.append({'line_no': line_no, 'text': raw})
            continue

        minute_of_day = parsed.hour * 60 + parsed.minute
        if previous_minutes is not None and minute_of_day < previous_minutes:
            timestamp_order_issues.append({
                'line_no': line_no,
                'time': hhmm,
                'previous_time': previous_time,
                'text': raw,
            })

        previous_minutes = minute_of_day
        previous_time = hhmm

    return {
        'path': str(path),
        'malformed': malformed,
        'timestamp_order_issues': timestamp_order_issues,
    }


def memory_doctor(paths: JournalPaths, days: int = 7) -> dict[str, object]:
    files = iter_daily_files(paths, days=max(1, days))
    daily_reports = [daily_file_health(path) for path in files]
    malformed = [
        {'path': report['path'], **item}
        for report in daily_reports
        for item in report['malformed']
    ]
    timestamp_order_issues = [
        {'path': report['path'], **item}
        for report in daily_reports
        for item in report['timestamp_order_issues']
    ]
    long_duplicates = long_memory_duplicates(paths)
    issue_count = len(malformed) + len(timestamp_order_issues) + len(long_duplicates)
    return {
        'days_scanned': max(1, days),
        'files_checked': len(files),
        'long_duplicates': long_duplicates,
        'malformed_daily_lines': malformed,
        'daily_timestamp_order_issues': timestamp_order_issues,
        'issue_count': issue_count,
        'status': 'ISSUES_FOUND' if issue_count else 'OK',
    }


def append_daily(paths: JournalPaths, note: str, dedupe_minutes: int = 0) -> bool:
    daily = paths.today_daily_path()
    paths.mem_dir.mkdir(parents=True, exist_ok=True)
    if is_recent_duplicate(paths, note, dedupe_minutes):
        return False
    ts = datetime.now().strftime('%H:%M')
    with daily.open('a', encoding='utf-8') as f:
        f.write(f"- {ts} {note.strip()}\n")
    return True


def append_long(paths: JournalPaths, note: str, dedupe: bool = True) -> bool:
    if dedupe and has_long_duplicate(paths, note):
        return False
    if not paths.long.exists():
        paths.long.write_text('# MEMORY.md\n\n', encoding='utf-8')
    with paths.long.open('a', encoding='utf-8') as f:
        f.write(f"\n- {note.strip()}\n")
    return True


def resolve_daily_ref(paths: JournalPaths, ref: str) -> dict[str, str]:
    m = DAILY_REF_RE.match(ref.strip())
    if not m:
        raise ValueError(f"Invalid daily ref '{ref}', expected YYYY-MM-DD.md:LINE")

    date_str, line_str = m.group(1), m.group(2)
    path = paths.mem_dir / f'{date_str}.md'
    if not path.exists():
        raise ValueError(f"Daily memory file not found for ref '{ref}'")

    try:
        line_no = int(line_str)
    except ValueError as exc:
        raise ValueError(f"Invalid line number in ref '{ref}'") from exc

    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception as exc:
        raise ValueError(f"Could not read daily memory file for ref '{ref}'") from exc

    if line_no < 1 or line_no > len(lines):
        raise ValueError(f"Ref '{ref}' points outside file bounds")

    raw = lines[line_no - 1].strip()
    m_line = LINE_RE.match(raw)
    if not m_line:
        raise ValueError(f"Ref '{ref}' does not point to a timestamped note line")

    hhmm, note = m_line.group(1), m_line.group(2)
    return {'date': date_str, 'time': hhmm, 'note': note, 'ref': ref, 'line_no': line_no, 'path': str(path)}


def daily_ref_context(paths: JournalPaths, ref: str, context_lines: int = 1) -> list[dict[str, object]]:
    item = resolve_daily_ref(paths, ref)
    if context_lines <= 0:
        return []

    path = Path(item['path'])
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    start = max(1, item['line_no'] - context_lines)
    end = min(len(lines), item['line_no'] + context_lines)
    excerpt: list[dict[str, object]] = []
    for idx in range(start, end + 1):
        excerpt.append({
            'line_no': idx,
            'text': lines[idx - 1],
            'is_target': idx == item['line_no'],
        })
    return excerpt


def promote_daily_ref(paths: JournalPaths, ref: str, prefix_date: bool = False, long_dedupe: bool = True) -> tuple[bool, str]:
    item = resolve_daily_ref(paths, ref)
    note = item['note']
    if prefix_date:
        note = f"{item['date']}: {note}"

    with global_lock(paths):
        added = append_long(paths, note, dedupe=long_dedupe)

    return added, note


def promote_candidate_refs(
    paths: JournalPaths,
    refs: list[str],
    prefix_date: bool = False,
    long_dedupe: bool = True,
    dry_run: bool = False,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    notes_to_write: list[str] = []
    seen_notes: set[str] = set()

    for ref in refs:
        item = resolve_daily_ref(paths, ref)
        note = item['note']
        if prefix_date:
            note = f"{item['date']}: {note}"

        normalized = normalize_note(note)
        already_present = (has_long_duplicate(paths, note) or normalized in seen_notes) if long_dedupe else False
        status = 'DRY_RUN' if dry_run else ('LONG_SKIP_DUPLICATE' if already_present else 'LONG_OK')
        results.append({
            'ref': ref,
            'note': note,
            'added': status == 'LONG_OK',
            'status': status,
        })

        if dry_run or already_present:
            continue

        notes_to_write.append(note)
        seen_notes.add(normalized)

    if notes_to_write:
        with global_lock(paths):
            for note in notes_to_write:
                append_long(paths, note, dedupe=False)

    return {
        'requested': len(refs),
        'added': sum(1 for item in results if item['added']),
        'skipped': sum(1 for item in results if item['status'] != 'LONG_OK'),
        'results': results,
    }


def init_memory_root(paths: JournalPaths, with_config: bool = False) -> dict:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.mem_dir.mkdir(parents=True, exist_ok=True)
    created = []
    if not paths.long.exists():
        paths.long.write_text('# MEMORY.md\n\n', encoding='utf-8')
        created.append(str(paths.long))
    if with_config:
        cfg = paths.root / 'agent-memory-journal.json'
        if not cfg.exists():
            cfg.write_text(json.dumps({'triggers': default_triggers()}, indent=2) + '\n', encoding='utf-8')
            created.append(str(cfg))
    return {'created': created, 'root': str(paths.root)}


def extract_candidates(text: str, triggers=None):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        low = ln.lower()
        if any(re.search(t, low) for t in (triggers or default_triggers())):
            out.append(ln)
    return out


def iter_daily_files(paths: JournalPaths, days: int, after_date=None, before_date=None):
    if not paths.mem_dir.exists():
        return []

    discovered = []
    for p in paths.mem_dir.glob('*.md'):
        m = DAILY_FILE_RE.match(p.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), '%Y-%m-%d').date()
        except ValueError:
            continue
        discovered.append((d, p))

    if not discovered:
        return []

    latest_file_date = max(d for d, _p in discovered)
    anchor_date = min(datetime.now().date(), latest_file_date) if not before_date else before_date

    # Treat --days as a lookback window in addition to the anchor date, so
    # --days 2 includes the anchor date plus the prior two dates. Using the
    # latest discovered file as a fallback anchor keeps historical/test roots
    # reviewable even when their notes are older than the real clock.
    rolling_cutoff = anchor_date - timedelta(days=max(0, days))
    min_date = max(rolling_cutoff, after_date) if after_date else rolling_cutoff
    max_date = before_date
    candidates = []
    for d, p in discovered:
        if d < min_date:
            continue
        if max_date and d > max_date:
            continue
        candidates.append((d, p))
    return [p for _d, p in sorted(candidates, key=lambda x: x[0], reverse=True)]


def parse_iso_date(value: str):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc


def collect_recent(paths: JournalPaths, days: int, limit: int, grep: str | None, after_date=None, before_date=None):
    files = iter_daily_files(paths, days, after_date, before_date)
    if not files:
        return []
    pattern = re.compile(grep, re.IGNORECASE) if grep else None
    out = []
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


def print_recent(paths: JournalPaths, days: int, limit: int, grep: str | None, as_json: bool = False, after_date=None, before_date=None):
    items = collect_recent(paths, days, limit, grep, after_date, before_date)
    if as_json:
        print(json.dumps(items, ensure_ascii=False))
        return
    files = iter_daily_files(paths, days, after_date, before_date)
    if not files:
        print('NO_MEMORY_FILES')
        return
    if not items:
        print('NO_MATCHES')
        return
    for item in items:
        print(f"{item['date']} {item['time']} {item['note']}")


def search_notes(paths: JournalPaths, query: str, days: int, limit: int, regex: bool = False, source: str = 'all', after_date=None, before_date=None):
    if regex:
        pattern = re.compile(query, re.IGNORECASE)
        matcher = lambda text: bool(pattern.search(text))
    else:
        needle = query.strip().lower()
        matcher = lambda text: needle in text.lower()
    out = []
    if source in ('all', 'long') and paths.long.exists():
        try:
            for idx, line in enumerate(paths.long.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
                if matcher(line):
                    out.append({'source': 'long', 'path': str(paths.long), 'line': idx, 'text': line})
                    if len(out) >= limit:
                        return out
        except Exception:
            pass
    if source in ('all', 'daily'):
        for p in iter_daily_files(paths, days, after_date, before_date):
            try:
                lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if matcher(line):
                    out.append({'source': 'daily', 'path': str(p), 'line': idx, 'text': line})
                    if len(out) >= limit:
                        return out
    return out


def print_search(paths: JournalPaths, **kwargs):
    as_json = kwargs.pop('as_json', False)
    items = search_notes(paths, **kwargs)
    if as_json:
        print(json.dumps(items, ensure_ascii=False))
        return
    if not items:
        print('NO_MATCHES')
        return
    for item in items:
        print(f"{item['source']} {item['path']}:{item['line']} {item['text']}")


def _note_words(paths: JournalPaths, days: int, after_date=None, before_date=None):
    files = iter_daily_files(paths, days, after_date=after_date, before_date=before_date)
    words = []
    notes = []
    stop = {
        'the','and','for','with','that','this','from','have','was','were','are','but','not','into','out','new','added','gained','now','also','recent','notes',
        'että','joka','tämä','tuo','ovat','oli','kun','tai','jos','nyt','sekä','vielä','kanssa','uusi','lisätty'
    }
    for p in files:
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
        for ln in lines:
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            note = m.group(2)
            notes.append(note)
            words.extend(w.lower() for w in re.findall(r"[A-Za-zÅÄÖåäö0-9-]{3,}", note) if w.lower() not in stop)
    return notes, words


def memory_stats(paths: JournalPaths, days: int = 7, top: int = 10):
    files = iter_daily_files(paths, days)
    note_count = 0
    hourly = Counter()
    daily_counts = Counter()
    notes, words = _note_words(paths, days)
    for p in files:
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
        for ln in lines:
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm = m.group(1)
            hour = hhmm.split(':')[0]
            note_count += 1
            hourly[hour] += 1
            daily_counts[p.stem] += 1
    return {
        'days_scanned': days,
        'files_found': len(files),
        'days_with_notes': len(daily_counts),
        'note_count': note_count,
        'busiest_hours': [{'hour': h, 'count': c} for h, c in hourly.most_common(3)],
        'top_words': [{'word': w, 'count': c} for w, c in Counter(words).most_common(top)],
    }


def memory_topics(paths: JournalPaths, days: int = 14, top: int = 8, samples: int = 2, min_count: int = 2, after_date=None, before_date=None):
    notes, words = _note_words(paths, days, after_date=after_date, before_date=before_date)
    counts = Counter(words)
    word_samples = {}
    for note in notes:
        tokens = set(tokenize(note))
        for word, count in counts.items():
            if count < min_count:
                continue
            if word in tokens:
                word_samples.setdefault(word, [])
                if len(word_samples[word]) < samples and note not in word_samples[word]:
                    word_samples[word].append(note)
    topics = []
    for word, count in counts.most_common():
        if count < min_count:
            continue
        topics.append({'word': word, 'count': count, 'samples': word_samples.get(word, [])})
        if len(topics) >= max(1, top):
            break
    return {'days_scanned': days, 'note_count': len(notes), 'topics': topics}


def print_stats(paths: JournalPaths, days: int = 7, top: int = 10, as_json: bool = False):
    stats = memory_stats(paths, days=max(1, days), top=max(1, top))
    if as_json:
        print(json.dumps(stats, ensure_ascii=False))
        return
    print(f"days_scanned={stats['days_scanned']} files_found={stats['files_found']} days_with_notes={stats['days_with_notes']} note_count={stats['note_count']}")
    if stats['busiest_hours']:
        print('busiest_hours: ' + ', '.join(f"{h['hour']}:00({h['count']})" for h in stats['busiest_hours']))
    if stats['top_words']:
        print('top_words: ' + ', '.join(f"{w['word']}({w['count']})" for w in stats['top_words']))


def print_topics(paths: JournalPaths, days: int = 14, top: int = 8, samples: int = 2, min_count: int = 2, as_json: bool = False):
    summary = memory_topics(paths, days=max(1, days), top=max(1, top), samples=max(1, samples), min_count=max(1, min_count))
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"days_scanned={summary['days_scanned']} note_count={summary['note_count']} topics={len(summary['topics'])}")
    for topic in summary['topics']:
        print(f"- {topic['word']}({topic['count']}): {' | '.join(topic['samples'])}")


def memory_cadence(paths: JournalPaths, days: int = 14, top_hours: int = 3, after_date=None, before_date=None):
    files = iter_daily_files(paths, days, after_date=after_date, before_date=before_date)
    per_day = []
    hourly = Counter()
    for p in files:
        count = 0
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
        for ln in lines:
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            count += 1
            hourly[m.group(1).split(':')[0]] += 1
        per_day.append({'date': p.stem, 'count': count})
    return {'days_scanned': days, 'per_day': per_day, 'busiest_hours': [{'hour': h, 'count': c} for h, c in hourly.most_common(top_hours)]}


def print_cadence(paths: JournalPaths, days: int = 14, top_hours: int = 3, as_json: bool = False):
    summary = memory_cadence(paths, days=max(1, days), top_hours=max(1, top_hours))
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    print('per_day: ' + ', '.join(f"{d['date']}({d['count']})" for d in summary['per_day']))
    print('busiest_hours: ' + ', '.join(f"{h['hour']}:00({h['count']})" for h in summary['busiest_hours']))


def memory_digest(paths: JournalPaths, days: int = 7, recent_limit: int = 5, top: int = 5, after_date=None, before_date=None):
    stats = memory_stats(paths, days=max(1, days), top=max(1, top))
    cadence = memory_cadence(paths, days=max(1, days), top_hours=max(1, min(top, 3)), after_date=after_date, before_date=before_date)
    topics = memory_topics(paths, days=max(1, days), top=max(1, top), samples=1, min_count=2, after_date=after_date, before_date=before_date)
    recent = collect_recent(paths, days=max(1, days), limit=max(1, recent_limit), grep=None, after_date=after_date, before_date=before_date)
    return {'days_scanned': days, 'stats': stats, 'cadence': cadence, 'topics': topics, 'recent': recent}


def print_digest(paths: JournalPaths, days: int = 7, recent_limit: int = 5, top: int = 5, as_json: bool = False):
    summary = memory_digest(paths, days=max(1, days), recent_limit=max(1, recent_limit), top=max(1, top))
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    stats = summary['stats']; cadence = summary['cadence']; topics = summary['topics']; recent = summary['recent']
    print(f"days_scanned={summary['days_scanned']} files_found={stats['files_found']} days_with_notes={stats['days_with_notes']} note_count={stats['note_count']}")
    if cadence['busiest_hours']:
        print('busiest_hours: ' + ', '.join(f"{h['hour']}:00({h['count']})" for h in cadence['busiest_hours']))
    if topics['topics']:
        print('topics: ' + ', '.join(f"{item['word']}({item['count']})" for item in topics['topics']))
    else:
        print('topics: none')
    if recent:
        print('recent_notes:')
        for item in recent:
            print(f"- {item['date']} {item['time']} {item['note']}")
    else:
        print('recent_notes: none')


def memory_candidates(
    paths: JournalPaths,
    days: int = 7,
    limit: int = 10,
    min_score: int = 2,
    triggers=None,
    pending_only: bool = False,
    after_date=None,
    before_date=None,
):
    topic_words = {
        item['word']
        for item in memory_topics(paths, days=max(1, days), top=20, samples=1, min_count=2, after_date=after_date, before_date=before_date)['topics']
    }
    out = []
    for p in iter_daily_files(paths, days, after_date=after_date, before_date=before_date):
        try:
            lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
        for idx, ln in enumerate(lines, start=1):
            m = LINE_RE.match(ln.strip())
            if not m:
                continue
            hhmm, note = m.group(1), m.group(2)
            low = note.lower()
            tokens = set(tokenize(note))
            score = 0
            reasons = []
            triggered = [t for t in (triggers or default_triggers()) if re.search(t, low)]
            if triggered:
                score += len(triggered)
                reasons.append('trigger_phrase')
            recurring = sorted(word for word in topic_words if word in tokens)
            if recurring:
                score += 1
                reasons.append(f"recurring_topic:{','.join(recurring[:3])}")
            if len(note) > 80:
                score += 1
                reasons.append('substantial_note')
            already_in_long_memory = has_long_duplicate(paths, note) or has_long_duplicate(paths, f"{p.stem}: {note}")
            if pending_only and already_in_long_memory:
                continue
            if score >= min_score:
                out.append({
                    'ref': f'{p.stem}.md:{idx}',
                    'date': p.stem,
                    'time': hhmm,
                    'note': note,
                    'score': score,
                    'reasons': reasons,
                    'already_in_long_memory': already_in_long_memory,
                })
    out.sort(key=lambda x: (-x['score'], x['ref']), reverse=False)
    return {
        'days_scanned': days,
        'candidate_count': len(out),
        'pending_only': pending_only,
        'candidates': out[: max(1, limit)],
    }


def print_candidates(
    paths: JournalPaths,
    days: int = 7,
    limit: int = 10,
    min_score: int = 2,
    as_json: bool = False,
    triggers=None,
    pending_only: bool = False,
    after_date=None,
    before_date=None,
):
    summary = memory_candidates(
        paths,
        days=max(1, days),
        limit=max(1, limit),
        min_score=max(1, min_score),
        triggers=triggers,
        pending_only=pending_only,
        after_date=after_date,
        before_date=before_date,
    )
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    if not summary['candidates']:
        print('NO_CANDIDATES')
        return
    for item in summary['candidates']:
        reasons = ', '.join(item['reasons']) if item['reasons'] else 'none'
        long_flag = 'yes' if item['already_in_long_memory'] else 'no'
        print(f"score={item['score']} {item['ref']} {item['time']} reasons={reasons} already_in_long_memory={long_flag}")
        print(f"  {item['note']}")


def related_long_matches(paths: JournalPaths, note: str, limit: int = 3) -> list[dict[str, object]]:
    if not paths.long.exists():
        return []

    note_tokens = set(tokenize(note))
    if not note_tokens:
        return []

    try:
        lines = paths.long.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return []

    matches = []
    for i, ln in enumerate(lines, 1):
        m = LONG_BULLET_RE.match(ln.strip())
        if not m:
            continue
        long_note = m.group(1)
        overlap = sorted(note_tokens & set(tokenize(long_note)))
        if not overlap:
            continue
        matches.append({
            'ref': f'{paths.long.name}:{i}',
            'note': long_note,
            'overlap_count': len(overlap),
            'overlap_tokens': overlap[:5],
        })

    matches.sort(key=lambda item: (-int(item['overlap_count']), item['ref']))
    return matches[: max(1, limit)]


def memory_review(
    paths: JournalPaths,
    days: int = 7,
    limit: int = 10,
    min_score: int = 2,
    triggers=None,
    pending_only: bool = False,
    related_limit: int = 3,
    context_lines: int = 0,
    after_date=None,
    before_date=None,
) -> dict:
    summary = memory_candidates(
        paths,
        days=max(1, days),
        limit=max(1, limit),
        min_score=max(1, min_score),
        triggers=triggers,
        pending_only=pending_only,
        after_date=after_date,
        before_date=before_date,
    )
    reviewed = []
    reason_counts = Counter()
    batch_refs = []

    for item in summary['candidates']:
        reason_counts.update(item.get('reasons', []))
        if not item.get('already_in_long_memory'):
            batch_refs.append(item['ref'])

        reviewed.append({
            **item,
            'promote_command': f"{Path(__file__).name} --root {paths.root} promote --ref {item['ref']} --prefix-date",
            'related_long_matches': related_long_matches(paths, item['note'], limit=max(1, related_limit)),
            'source_context': daily_ref_context(paths, item['ref'], context_lines=max(0, context_lines)),
        })

    batch_promote_command = None
    if batch_refs:
        date_filters = ''
        if after_date:
            date_filters += f" --after {after_date.isoformat()}"
        if before_date:
            date_filters += f" --before {before_date.isoformat()}"
        batch_promote_command = (
            f"{Path(__file__).name} --root {paths.root} promote-candidates "
            f"--days {max(1, days)} --limit {max(1, limit)} --min-score {max(1, min_score)}{date_filters} --prefix-date"
        )

    return {
        'days_scanned': summary['days_scanned'],
        'candidate_count': summary['candidate_count'],
        'pending_only': summary['pending_only'],
        'related_limit': max(1, related_limit),
        'context_lines': max(0, context_lines),
        'reason_counts': dict(sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        'batch_ref_count': len(batch_refs),
        'batch_promote_command': batch_promote_command,
        'candidates': reviewed,
    }


def print_review(
    paths: JournalPaths,
    days: int = 7,
    limit: int = 10,
    min_score: int = 2,
    as_json: bool = False,
    triggers=None,
    pending_only: bool = False,
    related_limit: int = 3,
    context_lines: int = 0,
    after_date=None,
    before_date=None,
):
    summary = memory_review(
        paths,
        days=max(1, days),
        limit=max(1, limit),
        min_score=max(1, min_score),
        triggers=triggers,
        pending_only=pending_only,
        related_limit=max(1, related_limit),
        context_lines=max(0, context_lines),
        after_date=after_date,
        before_date=before_date,
    )
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(
        f"days_scanned={summary['days_scanned']} candidate_count={summary['candidate_count']} "
        f"pending_only={'yes' if summary['pending_only'] else 'no'} related_limit={summary['related_limit']} "
        f"context_lines={summary['context_lines']} batch_ref_count={summary['batch_ref_count']}"
    )
    if summary['reason_counts']:
        reasons = ', '.join(f"{reason}({count})" for reason, count in summary['reason_counts'].items())
        print(f"reason_counts: {reasons}")
    else:
        print('reason_counts: none')

    if summary['batch_promote_command']:
        print(f"batch_promote: {summary['batch_promote_command']}")
    else:
        print('batch_promote: none')

    if not summary['candidates']:
        print('NO_CANDIDATES')
        return
    for item in summary['candidates']:
        reasons = ', '.join(item['reasons']) if item['reasons'] else 'none'
        long_flag = 'yes' if item['already_in_long_memory'] else 'no'
        print(f"score={item['score']} {item['ref']} {item['time']} reasons={reasons} already_in_long_memory={long_flag}")
        print(f"  note: {item['note']}")
        print(f"  promote: {item['promote_command']}")
        if item['source_context']:
            print('  source_context:')
            for line in item['source_context']:
                marker = '>' if line['is_target'] else ' '
                print(f"    {marker} {line['line_no']}: {line['text']}")
        if item['related_long_matches']:
            print('  related_long_matches:')
            for match in item['related_long_matches']:
                overlap = ', '.join(match['overlap_tokens']) if match['overlap_tokens'] else 'none'
                print(f"    - {match['ref']} overlap={match['overlap_count']} tokens={overlap}")
                print(f"      {match['note']}")
        else:
            print('  related_long_matches: none')


def print_promote_candidates(
    paths: JournalPaths,
    days: int = 7,
    limit: int = 10,
    min_score: int = 2,
    prefix_date: bool = False,
    long_dedupe: bool = True,
    dry_run: bool = False,
    as_json: bool = False,
    triggers=None,
    after_date: datetime.date | None = None,
    before_date: datetime.date | None = None,
):
    candidates = memory_candidates(
        paths,
        days=max(1, days),
        limit=max(1, limit),
        min_score=max(1, min_score),
        triggers=triggers,
        pending_only=True,
        after_date=after_date,
        before_date=before_date,
    )
    refs = [item['ref'] for item in candidates['candidates'] if not item.get('already_in_long_memory')]
    summary = promote_candidate_refs(
        paths,
        refs=refs,
        prefix_date=prefix_date,
        long_dedupe=long_dedupe,
        dry_run=dry_run,
    )
    summary.update({
        'days_scanned': candidates['days_scanned'],
        'candidate_count': candidates['candidate_count'],
    })

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    print(
        f"days_scanned={summary['days_scanned']} candidate_count={summary['candidate_count']} "
        f"requested={summary['requested']} added={summary['added']} skipped={summary['skipped']}"
    )
    if not summary['results']:
        print('NO_PROMOTION_TARGETS')
        return

    for item in summary['results']:
        print(f"{item['status']} {item['ref']} {item['note']}")


def print_doctor(paths: JournalPaths, days: int = 7, as_json: bool = False):
    summary = memory_doctor(paths, days=max(1, days))

    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return

    print(f"status={summary['status']} files_checked={summary['files_checked']} issue_count={summary['issue_count']}")

    if summary['long_duplicates']:
        print('long_duplicates:')
        for item in summary['long_duplicates']:
            print(f"- count={item['count']} lines={','.join(str(n) for n in item['lines'])} {item['note']}")
    else:
        print('long_duplicates: none')

    if summary['malformed_daily_lines']:
        print('malformed_daily_lines:')
        for item in summary['malformed_daily_lines']:
            print(f"- {item['path']}:{item['line_no']} {item['text']}")
    else:
        print('malformed_daily_lines: none')

    if summary['daily_timestamp_order_issues']:
        print('daily_timestamp_order_issues:')
        for item in summary['daily_timestamp_order_issues']:
            print(f"- {item['path']}:{item['line_no']} time={item['time']} prev={item['previous_time']} {item['text']}")
    else:
        print('daily_timestamp_order_issues: none')


def build_parser():
    ap = argparse.ArgumentParser(
        description='Durable memory journal for agents and operators',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agent-memory-journal --root /workspace add --note \"Remember to rotate PAT\"\n"
            "  agent-memory-journal --root /workspace recent --days 2\n"
            "  agent-memory-journal --root /workspace digest --days 7"
        ),
    )
    ap.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    ap.add_argument('--root', type=Path, default=default_root(), help='Memory root directory (default: AGENT_MEMORY_ROOT env or current directory)')
    ap.add_argument('--memory-dir', default='memory', help='Daily memory directory relative to root (default: memory)')
    ap.add_argument('--long-file', default='MEMORY.md', help='Long-term memory filename relative to root (default: MEMORY.md)')
    ap.add_argument('--config-file', help='Optional JSON config path relative to root or absolute')
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='Append a note to daily memory')
    a.add_argument('--note', required=True)
    a.add_argument('--long', action='store_true')
    a.add_argument('--dedupe-minutes', type=int, default=0)
    a.add_argument('--no-long-dedupe', action='store_true')

    i = sub.add_parser('init', help='Bootstrap a new memory root')
    i.add_argument('--with-config', action='store_true', help='Create starter agent-memory-journal.json too')

    ex = sub.add_parser('extract', help='Extract likely memory-worthy lines from stdin or file')
    ex.add_argument('--file', type=Path)

    r = sub.add_parser('recent', help='Show newest daily memory notes across recent days')
    r.add_argument('--days', type=int, default=2)
    r.add_argument('--limit', type=int, default=20)
    r.add_argument('--grep')
    r.add_argument('--after', type=parse_iso_date)
    r.add_argument('--before', type=parse_iso_date)
    r.add_argument('--json', action='store_true')

    s = sub.add_parser('search', help='Search long and daily notes for text matches')
    s.add_argument('--query', required=True)
    s.add_argument('--days', type=int, default=30)
    s.add_argument('--limit', type=int, default=20)
    s.add_argument('--regex', action='store_true')
    s.add_argument('--source', choices=['all', 'long', 'daily'], default='all')
    s.add_argument('--after', type=parse_iso_date)
    s.add_argument('--before', type=parse_iso_date)
    s.add_argument('--json', action='store_true')

    st = sub.add_parser('stats', help='Summarize recent daily memory activity')
    st.add_argument('--days', type=int, default=7)
    st.add_argument('--top', type=int, default=10)
    st.add_argument('--json', action='store_true')

    tp = sub.add_parser('topics', help='Surface recurring note topics with sample references')
    tp.add_argument('--days', type=int, default=14)
    tp.add_argument('--top', type=int, default=8)
    tp.add_argument('--samples', type=int, default=2)
    tp.add_argument('--min-count', type=int, default=2)
    tp.add_argument('--json', action='store_true')

    cd = sub.add_parser('cadence', help='Show daily note volume and busiest hours')
    cd.add_argument('--days', type=int, default=14)
    cd.add_argument('--top-hours', type=int, default=3)
    cd.add_argument('--json', action='store_true')

    dg = sub.add_parser('digest', help='Print a compact operational digest')
    dg.add_argument('--days', type=int, default=7)
    dg.add_argument('--recent-limit', type=int, default=5)
    dg.add_argument('--top', type=int, default=5)
    dg.add_argument('--json', action='store_true')

    dc = sub.add_parser('doctor', help='Audit memory files for duplicates and malformed daily note lines')
    dc.add_argument('--days', type=int, default=14)
    dc.add_argument('--json', action='store_true')

    cc = sub.add_parser('candidates', help='Surface likely long-term memory candidates')
    cc.add_argument('--days', type=int, default=7)
    cc.add_argument('--limit', type=int, default=10)
    cc.add_argument('--min-score', type=int, default=2)
    cc.add_argument('--after', type=parse_iso_date)
    cc.add_argument('--before', type=parse_iso_date)
    cc.add_argument('--pending-only', action='store_true', help='Only show candidates not already present in long-term memory')
    cc.add_argument('--json', action='store_true')

    rv = sub.add_parser('review', help='Review candidate notes with related long-memory matches and promote commands')
    rv.add_argument('--days', type=int, default=7)
    rv.add_argument('--limit', type=int, default=10)
    rv.add_argument('--min-score', type=int, default=2)
    rv.add_argument('--after', type=parse_iso_date)
    rv.add_argument('--before', type=parse_iso_date)
    rv.add_argument('--pending-only', action='store_true')
    rv.add_argument('--related-limit', type=int, default=3)
    rv.add_argument('--context-lines', type=int, default=0)
    rv.add_argument('--json', action='store_true')

    pr = sub.add_parser('promote', help='Promote a timestamped daily memory note into MEMORY.md by ref')
    pr.add_argument('--ref', required=True, help='Daily note ref in the form YYYY-MM-DD.md:LINE')
    pr.add_argument('--prefix-date', action='store_true', help='Prefix the promoted note with its source date')
    pr.add_argument('--long-dedupe', action=argparse.BooleanOptionalAction, default=True, help='Skip appending when an equivalent MEMORY.md bullet already exists (default: true)')

    pc = sub.add_parser('promote-candidates', help='Promote recent high-signal daily notes into MEMORY.md in one pass')
    pc.add_argument('--days', type=int, default=7)
    pc.add_argument('--limit', type=int, default=10)
    pc.add_argument('--min-score', type=int, default=2)
    pc.add_argument('--after', type=parse_iso_date)
    pc.add_argument('--before', type=parse_iso_date)
    pc.add_argument('--prefix-date', action='store_true')
    pc.add_argument('--long-dedupe', action=argparse.BooleanOptionalAction, default=True, help='Skip appending when an equivalent MEMORY.md bullet already exists (default: true)')
    pc.add_argument('--dry-run', action='store_true', help='Preview promotions without writing to MEMORY.md')
    pc.add_argument('--json', action='store_true')
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    paths = JournalPaths(args.root.expanduser().resolve(), args.memory_dir, args.long_file)
    config = load_config(paths, args.config_file)
    triggers = config['triggers']
    if args.cmd == 'init':
        with global_lock(paths):
            result = init_memory_root(paths, with_config=args.with_config)
        print(json.dumps(result, ensure_ascii=False))
    elif args.cmd == 'add':
        with global_lock(paths):
            added_daily = append_daily(paths, args.note, dedupe_minutes=args.dedupe_minutes)
            print('OK: note stored' if added_daily else 'SKIP_DUPLICATE: recent identical note exists')
            if args.long:
                added_long = append_long(paths, args.note, dedupe=not args.no_long_dedupe)
                print('LONG_OK' if added_long else 'LONG_SKIP_DUPLICATE')
    elif args.cmd == 'extract':
        text = args.file.read_text(encoding='utf-8') if args.file else __import__('sys').stdin.read()
        c = extract_candidates(text, triggers=triggers)
        print(json.dumps(c, ensure_ascii=False, indent=2))
    elif args.cmd == 'recent':
        if args.after and args.before and args.after > args.before:
            raise SystemExit("Invalid date range: --after cannot be later than --before")
        print_recent(paths, days=max(1, args.days), limit=max(1, args.limit), grep=args.grep, as_json=args.json, after_date=args.after, before_date=args.before)
    elif args.cmd == 'search':
        print_search(paths, query=args.query, days=max(1, args.days), limit=max(1, args.limit), regex=args.regex, source=args.source, after_date=args.after, before_date=args.before, as_json=args.json)
    elif args.cmd == 'stats':
        print_stats(paths, days=max(1, args.days), top=max(1, args.top), as_json=args.json)
    elif args.cmd == 'topics':
        print_topics(paths, days=max(1, args.days), top=max(1, args.top), samples=max(1, args.samples), min_count=max(1, args.min_count), as_json=args.json)
    elif args.cmd == 'cadence':
        print_cadence(paths, days=max(1, args.days), top_hours=max(1, args.top_hours), as_json=args.json)
    elif args.cmd == 'digest':
        print_digest(paths, days=max(1, args.days), recent_limit=max(1, args.recent_limit), top=max(1, args.top), as_json=args.json)
    elif args.cmd == 'doctor':
        print_doctor(paths, days=max(1, args.days), as_json=args.json)
    elif args.cmd == 'candidates':
        if args.after and args.before and args.after > args.before:
            raise SystemExit("Invalid date range: --after cannot be later than --before")
        print_candidates(
            paths,
            days=max(1, args.days),
            limit=max(1, args.limit),
            min_score=max(1, args.min_score),
            as_json=args.json,
            triggers=triggers,
            pending_only=args.pending_only,
            after_date=args.after,
            before_date=args.before,
        )
    elif args.cmd == 'review':
        if args.after and args.before and args.after > args.before:
            raise SystemExit("Invalid date range: --after cannot be later than --before")
        print_review(
            paths,
            days=max(1, args.days),
            limit=max(1, args.limit),
            min_score=max(1, args.min_score),
            as_json=args.json,
            triggers=triggers,
            pending_only=args.pending_only,
            related_limit=max(1, args.related_limit),
            context_lines=max(0, args.context_lines),
            after_date=args.after,
            before_date=args.before,
        )
    elif args.cmd == 'promote':
        try:
            added, note = promote_daily_ref(
                paths,
                ref=args.ref,
                prefix_date=args.prefix_date,
                long_dedupe=args.long_dedupe,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"LONG_OK {note}" if added else f"LONG_SKIP_DUPLICATE {note}")
    elif args.cmd == 'promote-candidates':
        if args.after and args.before and args.after > args.before:
            raise SystemExit("Invalid date range: --after cannot be later than --before")
        print_promote_candidates(
            paths,
            days=max(1, args.days),
            limit=max(1, args.limit),
            min_score=max(1, args.min_score),
            prefix_date=args.prefix_date,
            long_dedupe=args.long_dedupe,
            dry_run=args.dry_run,
            as_json=args.json,
            triggers=triggers,
            after_date=args.after,
            before_date=args.before,
        )


if __name__ == '__main__':
    main()
