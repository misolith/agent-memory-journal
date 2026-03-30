# agent-memory-journal

A lightweight, file-based memory journal for agents and operators.

`agent-memory-journal` helps keep short-term notes, long-term memory, and compact review workflows in sync without needing a database or external service. It is designed for agent setups that want durable memory with minimal moving parts.

## Status

This repository is the public productization track.

The internal production version still lives separately in the main OpenClaw workspace. This repo is where cleanup, parameterization, packaging, tests, and public-facing documentation happen before any internal migration.

## Core capabilities

- append daily notes with duplicate protection
- optionally append long-term memory bullets
- search recent notes and long-term memory
- show recent activity and memory cadence
- surface recurring topics
- generate compact operational digests
- suggest likely long-term memory candidates from recent daily notes

## CLI examples

```bash
agent-memory-journal add --note "Remember to renew the PAT before Friday"
agent-memory-journal add --note "Use WiseGolf app path for live tee time checks" --long
agent-memory-journal recent --days 2
agent-memory-journal search --query "golf"
agent-memory-journal topics --days 14
agent-memory-journal cadence --days 14
agent-memory-journal digest --days 7
agent-memory-journal candidates --days 7
```

## Current implementation notes

The current script still reflects its origin as an internal workspace tool and will be refactored in-place here:

- remove hard-coded workspace paths
- support configurable memory roots
- document expected directory layout
- add lightweight tests for duplicate handling and summaries
- package cleanly for standalone use

## Repository layout

```text
agent-memory-journal/
├── agent_memory_journal.py
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── examples/
│   └── quickstart.md
└── tests/
    └── test_smoke.py
```

## Development

Create a local virtual environment and run tests:

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest -q
```

## License

MIT
