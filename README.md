# Agent Memory Journal V2 (Zeus)

A robust 3-tier memory system for autonomous agents.

## Features

- **3-Tier Storage**:
    - **Hot** (`AGENT.md`): Pinned items always in context.
    - **Warm** (`core/`): Curated long-term memories (decisions, constraints, etc.).
    - **Cold** (`episodic/`): Daily logs of events and observations.
- **Probabilistic Recall**: Uses BM25 for ranked retrieval across all tiers.
- **Weighted Search**: Warm memories outrank episodic logs.
- **Autonomous Promotion**: Repeated episodic notes are automatically promoted to Core.
- **Integrity Checks**: Manifest-based verification of memory files.
- **Safety**: Built-in sanitation and prompt-injection defense for Core memories.

## Installation

```bash
pip install .
```

## CLI Usage

```bash
# Add a daily note
agent-memory-journal note "Miso prefers dark mode" --category preference

# Add a core constraint (pinned to AGENT.md)
agent-memory-journal remember "Never use public wifi" --category constraint --pinned

# Search all tiers
agent-memory-journal search --query "preferences"

# Mark a memory as superseded
agent-memory-journal forget dec-1234567890

# Integrity check
agent-memory-journal doctor --strict
```

## API Usage

```python
from agent_memory import Journal

j = Journal(root="~/.memory")
j.init()

# Store episodic memory
j.note("User mentioned Arc Raiders interest")

# Search (Warm hits weighted 1.5x)
hits = j.recall("games")

# Promote candidates & rebuild AGENT.md
j.ingest()
```
