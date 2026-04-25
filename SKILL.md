---
name: agent-memory-journal
description: Layered agent memory for hot, warm, and cold recall. Use the v2 Python API by default. Use LegacyJournal only when explicitly working with old MEMORY.md + memory/YYYY-MM-DD.md layouts.
---

# Agent Memory Journal

## V2 usage direction

Prefer the importable Python API over shelling out to the CLI when integrating with an agent.

Recommended flow:
- initialize `.memory/` with `Journal.init()`
- write episodic notes with `note(...)`
- write pinned durable constraints with `remember(...)`
- record review-loop findings with `session_note(...)` or `review_memory.log_review_findings(...)`
- run promotion and rebuild with `ingest()`
- query durable warm memory with `recall_core(...)`

## Legacy compatibility

For old layout migrations:
- use `LegacyJournal`
- or run `python3 agent_memory_journal.py ...` directly
