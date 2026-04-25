# agent-memory-journal

Layered agent memory for hot, warm, and cold recall.

## Status

This branch is the v2 direction. The primary API is `agent_memory.Journal`, which targets the `.memory/` layout. Legacy `MEMORY.md` + `memory/YYYY-MM-DD.md` flows remain available through `LegacyJournal` and the old CLI during migration.

## Layout

```text
.memory/
├── AGENT.md
├── core/
├── episodic/
├── sessions/
├── archive/core/
└── index/
```

## Quick v2 examples

```python
from agent_memory import Journal

j = Journal(root='.')
j.init()
j.note('Decision: keep AGENT hot set tiny', category='decision', importance='high')
j.remember('AGENT.md must stay small and pinned-only', category='constraint', pinned=True)
j.session_note('review-42', 'Pinned detection is too loose', category='gotcha', importance='high')

hits = j.recall_core('pinned hot set', k=5)
report = j.ingest()
```

## Legacy compatibility

If you still need the old file layout, use:

```python
from agent_memory.api import LegacyJournal
legacy = LegacyJournal(root='.')
legacy.note('Old style note')
```
