# memory-recall-guard

A lightweight CLI for durable agent memory journaling, recall, and review.

`memory-recall-guard` helps an agent or operator keep daily notes, long-term memory, and compact review workflows in sync without needing a database or external service.

## What it does

- append daily notes with duplicate protection
- optionally append long-term memory bullets
- search recent notes and long-term memory
- surface recurring topics and busiest logging hours
- generate compact operational digests
- suggest likely long-term memory candidates from recent daily notes

## Current status

This repository is the productization track for the tool.

The internal production version still lives in the main OpenClaw workspace. This repo is where cleanup, parameterization, packaging, tests, and public-facing documentation happen before any internal migration.

## Planned CLI

```bash
python3 memory_recall_guard.py add --note "Remember to rotate the PAT today"
python3 memory_recall_guard.py recent --days 2
python3 memory_recall_guard.py search --query "golf"
python3 memory_recall_guard.py topics --days 14
python3 memory_recall_guard.py cadence --days 14
python3 memory_recall_guard.py digest --days 7
python3 memory_recall_guard.py candidates --days 7
```

## Productization goals

- remove hard-coded workspace paths
- support configurable memory root
- document file layout and expected outputs
- add lightweight tests for duplicate handling and summaries
- package cleanly for standalone use

## Repository layout

```text
memory-recall-guard/
├── memory_recall_guard.py
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── examples/
│   └── quickstart.md
└── tests/
    └── test_smoke.py
```

## License

MIT
