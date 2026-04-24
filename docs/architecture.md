# Architecture

## Goal

`agent-memory-journal` is being re-architected from a file-oriented journaling CLI into a layered agent memory system with explicit hot, warm, and cold tiers.

## Target layout

```text
<memory-root>/
├── AGENT.md
├── core/
│   ├── decisions.md
│   ├── constraints.md
│   ├── gotchas.md
│   ├── preferences.md
│   └── capabilities.md
├── episodic/
│   ├── 2026-04-24.md
│   └── ...
├── sessions/
│   ├── <session-id>.md
│   └── ...
├── archive/
│   └── core/
│       ├── decisions.md
│       ├── constraints.md
│       ├── gotchas.md
│       ├── preferences.md
│       └── capabilities.md
└── index/
    ├── manifest.json
    ├── recall.sqlite
    └── embeddings.sqlite
```

## Tier semantics

### 1. AGENT.md
Purpose:
- always-context hot set
- tiny, stable, behavior-changing memory only

Rules:
- generated from reviewed/pinned core memory
- not the source of truth for broad history
- V1 hard limit: 2048 characters, with token-based enforcement planned as a follow-up tightening
- if over limit, validation fails

### 2. core/
Purpose:
- durable warm memory
- categorized, recallable, auditable working knowledge

Rules:
- one file per durable category
- entries carry metadata and stable ids
- primary surface for on-demand recall
- subject to decay, archive, and supersedes transitions

### 3. episodic/
Purpose:
- cold append-oriented history
- raw observations, events, daily notes, transient facts

Rules:
- append-friendly
- source material for candidate generation
- not loaded by default into hot context

### 4. sessions/
Purpose:
- short-term memory within one agent/session execution scope
- allows subagents and primary agent to share transient context without polluting long-term memory directly

Rules:
- TTL bound to session lifecycle or explicit cleanup policy
- repeated claims across sessions may become promotion candidates

### 5. archive/
Purpose:
- preserve warm memory that is no longer active
- maintain audit trail without cluttering current recall surface

Rules:
- archive is reversible
- archived items keep provenance and ids
- superseded items may remain in archive or active files with explicit state markers, depending on implementation choice

### 6. index/
Purpose:
- acceleration and integrity layer
- separates retrieval/index data from source-of-truth markdown

Contents:
- `manifest.json`: checksums, schema version, file inventory
- `recall.sqlite`: lexical ranking indexes and metadata caches
- `embeddings.sqlite`: optional semantic index

## Canonical data flow

```text
user/agent/subagent input
  -> sessions/ or episodic/
  -> candidate extraction
  -> categorized core memory
  -> reviewed/pinned hot memory in AGENT.md
```

This flow is intentionally one-way by default. Hot memory is derived from warm memory. Warm memory is derived from episodic/session evidence. Raw history does not jump directly into always-context memory without policy.

## Memory object model

Every durable memory item should support at least the following logical fields:
- `id`
- `text`
- `category`
- `tier`
- `state`
- `source`
- `created_at`
- `updated_at`
- `refs`
- `occurrences`
- `score`
- `pinned`
- `supersedes`
- `confidence`

The markdown storage format may remain human-readable, but the logical model must be explicit in code.

## Backward compatibility and migration

Current layout:
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

Migration target:
- `MEMORY.md` content split into `core/` category files
- `memory/YYYY-MM-DD.md` imported into `episodic/`

Migration principles:
- migration must be explicit and auditable
- no silent destructive rewrite
- import mode may continue supporting legacy layout for a while
- new feature development should target the new layout, not deepen legacy coupling

## Code architecture

The current monolithic script should be split into a package.

Target modules:
- `agent_memory/models.py`
- `agent_memory/storage.py`
- `agent_memory/promote.py`
- `agent_memory/recall.py`
- `agent_memory/security.py`
- `agent_memory/api.py`
- `agent_memory/cli.py`

### Responsibilities
- `models.py`: typed memory records, candidate records, result objects, state enums
- `storage.py`: markdown I/O, path discipline, migration helpers, manifest reads/writes
- `promote.py`: candidate extraction, scoring, promotion, decay, supersedes
- `recall.py`: exact search, BM25 ranking, semantic adapter layer
- `security.py`: provenance checks (`user|agent|subagent|import`), sanitization, path validation, integrity rules
- `api.py`: public Python interface
- `cli.py`: command-line wrappers over API

## Validation boundaries

The architecture relies on three important enforcement boundaries:

1. **Hot boundary**
   - only reviewed or pinned memory reaches `AGENT.md`

2. **Trust boundary**
   - provenance influences promotion eligibility

3. **Growth boundary**
   - hot and warm layers have hard size/entry limits

## Success condition

The architecture is correct when:
- hot memory is tiny and always useful
- warm memory is structured and recallable
- cold memory remains auditable but cheap to ignore
- promotion is deterministic enough to trust
- the codebase exposes a Python API that an agent can import directly without shelling out to CLI commands
