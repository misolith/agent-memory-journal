# Skill: Agent Memory Journal

Manage and retrieve long-term memory using a 3-tier structure (Hot, Warm, Cold).

## Tools

- `agent-memory-journal note <text>`: Add episodic note.
- `agent-memory-journal remember <text> --category <cat>`: Add core memory.
- `agent-memory-journal search --query <q>`: Search memory.
- `agent-memory-journal forget <id>`: Supersede a memory.
- `agent-memory-journal ingest`: Run promotion and rebuild cycle.

## Core Categories

- `decision`: Strategic choices.
- `constraint`: Hard rules or limitations.
- `gotcha`: Lessons learned or bugs.
- `preference`: User or agent preferences.
- `capability`: New skills or tools.

## Guidelines

1.  **Episodic first**: Use `note` for observations.
2.  **Explicit curation**: Use `remember` for facts that must persist.
3.  **Atomic pinning**: Use `--pinned` for items that MUST be in `AGENT.md`.
4.  **Verification**: Run `doctor` periodically to ensure integrity.
