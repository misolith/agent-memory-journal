# Changelog

## Unreleased
- add agent installation guide for workspace embedding and CLI bootstrap
- add `.memory/config.json` support for overriding the hot promotion target, header, and size limit
- document how to promote pinned hot memory into files like root-level `AGENTS.md`

## 0.2.0 (2026-04-25)
- **3-Tier Memory Architecture**: Implemented `.memory/` layout with Hot (`AGENT.md`), Warm (`core/`), and Cold (`episodic/`) tiers.
- **Probabilistic Retrieval**: Replaced substring search with **BM25 ranking** for all recall operations.
- **Weighted Recall**: Warm (Core) memories now outrank Episodic logs in unified search (1.5x score multiplier).
- **Atomic Persistence**: Implemented "write-to-temp-then-rename" for all file operations to prevent corruption.
- **"Forget" Capability**: Added `forget` command and API method to supersede memories by ID.
- **Autonomous Promotion**: Automated detection and promotion of repeated facts from episodic to core memory.
- **Integrity Doctor**: Manifest-based verification of core memory files with SHA256 checksums.
- **Safety Boundary**: Strict sanitation for Hot/Core tiers while allowing raw evidence in Episodic logs.
- **Session Support**: Isolated session memory tracking with cross-session klustering.
- **Decay & Archive**: 30-day unpinned memory archival to prevent "junk drawer" core files.
- **Migration Path**: Built-in `migrate` command to port legacy `MEMORY.md` and `memory/` folders.

## 0.1.0
- initialize standalone `agent-memory-journal` repository
- rename CLI engine to `agent_memory_journal.py`
- decouple memory root from workspace-specific hard-coded paths
- add JSON config for trigger patterns
- add agent-facing `SKILL.md` and installation guidance
- expand README with layout, config, testing, and roadmap
- add CLI, JSON, config, and help/version tests
