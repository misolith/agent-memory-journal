
## Unreleased
- added a `review` command that shows candidate notes alongside related `MEMORY.md` bullets and copyable promotion commands
# Changelog

## Unreleased
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
