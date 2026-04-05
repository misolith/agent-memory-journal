# Changelog

## Unreleased
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
