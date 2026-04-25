
## Unreleased
- add `doctor --after/--before` so memory audits can target exact daily windows during cleanup and automation runs
- add a `doctor` command that audits duplicate long-memory bullets plus malformed or out-of-order daily note lines
- add `doctor --strict` so audit issues return a non-zero exit code for cron and CI workflows
- anchor rolling day-window scans to the latest discovered daily note when reviewing historical/test roots, so `review` and related commands still surface older notes reliably
- add `candidates --after/--before` and `review --after/--before` so promotion review can target exact daily windows
- preserve `review` date filters in emitted `batch_promote` commands so scoped promotion runs do not drift
- added a `review` command that shows candidate notes alongside related `MEMORY.md` bullets and copyable promotion commands
# Changelog

## 0.2.0
- add a dedicated v2 `.memory/` layout with hot, warm, cold, session, archive, and index directories
- add importable Journal API for v2 flows plus LegacyJournal compatibility during migration
- add repeated-memory promotion, hot-set rebuild, session memory collection, ingest cycle, and review-memory logging
- add integrity doctor + manifest verification, legacy import tooling, and archive/decay support
- add BM25-based core recall, memory metadata (`id`, `state`, `created`), and duplicate-id protection
- add security filtering for core/hot promotion while preserving episodic/session evidence capture
- expand README, SKILL guidance, and executable examples for v2 usage

## Unreleased
- make `--days` lookback windows inclusive of today plus the prior N dates so boundary-day review candidates are not dropped unexpectedly
- add `review --context-lines` so candidate review can include neighboring source lines before promotion
- add `promote` and `promote-candidates` to the public CLI so the packaged tool matches the documented alpha contract and internal production workflow
- add `candidates --pending-only` so promotion review can ignore notes already present in `MEMORY.md`
- enrich candidate output with stable refs, timestamps, heuristic reasons, and `already_in_long_memory` metadata
- cover pending-only candidate filtering in contract tests
- add `recent --after/--before` date filters so note review can target exact daily windows without grep hacks
- validate `recent` date ranges consistently with `search`
- cover recent date-range filtering in JSON CLI tests

## 0.1.0
- initialize standalone `agent-memory-journal` repository
- rename CLI engine to `agent_memory_journal.py`
- decouple memory root from workspace-specific hard-coded paths
- add JSON config for trigger patterns
- add agent-facing `SKILL.md` and installation guidance
- expand README with layout, config, testing, and roadmap
- add CLI, JSON, config, and help/version tests
