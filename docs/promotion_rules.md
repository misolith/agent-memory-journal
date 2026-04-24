# Promotion Rules

## Purpose

This document defines how memory moves through the system:

```text
sessions/ or episodic/
  -> candidate
  -> core/
  -> AGENT.md
```

The goal is to make long-term memory promotion explicit, reviewable, and resistant to uncontrolled growth.

## 1. Source tiers

### Session memory
- short-lived
- scoped to one active run, task, or multi-agent execution
- may contain useful transient facts
- may generate promotion candidates if the same claim recurs

### Episodic memory
- append-oriented historical log
- primary raw source for candidate extraction
- not durable by default just because it was written down once

### Core memory
- warm durable memory
- structured by category
- main target for repeated or intentional facts

### AGENT hot memory
- smallest and strictest layer
- generated from a subset of core memory
- reserved for facts that should shape default behavior every day

## 2. Candidate generation

A candidate is a normalized memory claim extracted from session or episodic data.

Each candidate must have:
- `id`
- `text`
- `normalized_claim`
- `category`
- `source_refs`
- `source_provenance`
- `occurrence_count`
- `distinct_day_count`
- `score`
- `score_breakdown`
- `state`

### Candidate sources
Candidates may be created from:
- explicit note entries
- explicit tags such as `remember:`
- repeated claims detected across days or sessions
- change-claim extraction patterns such as `can now`, `no longer`, `restored`, `revoked`, `now supports`

## 3. Categorization rules

No candidate reaches core memory without a category.

Allowed V1 categories:
- `decision`
- `constraint`
- `gotcha`
- `preference`
- `capability`

### Categorization priority
1. explicit category from API/tool call
2. explicit tag in source text
3. deterministic heuristic classifier
4. otherwise remain candidate-only until reviewed

## 4. Promote to core

A candidate may be promoted from session/episodic memory into core memory if one of the following is true:

### Rule A: repeated evidence
All conditions must hold:
- normalized claim appears on at least **2 distinct days** or in **2 distinct sessions**
- candidate has a valid category
- candidate has at least one supporting trigger or high-confidence change signal
- candidate is not blocked by trust or sanitization rules

### Rule B: explicit remember intent
All conditions must hold:
- source contains explicit durable-memory intent such as `remember:`
- candidate has a valid category
- source passes trust and sanitization checks

### Rule C: explicit API elevation
All conditions must hold:
- API call marks the note as high importance or equivalent
- category is provided or resolved confidently
- source provenance is accepted for core promotion

### Core promotion result
When promoted, the memory item must store:
- stable `id`
- canonical text
- category
- provenance summary
- refs to supporting source entries
- first_seen / last_seen
- occurrence counts
- state = `active`
- optional `supersedes`

## 5. Promote to AGENT.md

Promotion from core memory to `AGENT.md` is intentionally stricter.

### Required conditions
All conditions must hold:
- item already exists in core memory
- item is `active`
- item is marked `pinned=True` through review or explicit pin flow
- item is relevant to recurring day-to-day agent behavior
- source/provenance policy allows hot-memory inclusion
- resulting `AGENT.md` stays within hard size limit

### Default rule
Core memory does **not** automatically enter `AGENT.md` just because it is important.

The hot set is a curated execution surface, not a second copy of all durable memory.

## 6. Decay and archive

Core memory is not immortal.

### Archive candidate rule
A core item becomes an archive candidate if:
- it has not been referenced or refreshed in **30 days**
- it is not pinned for hot memory
- it has not been recently reaffirmed by new episodic/session evidence
- it is not protected by explicit retention policy

### Archive action
- item state becomes `archived`
- item moves to archive storage or is marked archived in place
- refs and provenance remain intact
- restoration must be possible

## 7. Supersedes

Newer facts may replace older ones without erasing history.

### Supersedes rule
A new memory item may declare `supersedes: <id>` if:
- it refers to the same conceptual fact or policy surface
- it clearly changes the operational truth of the older item
- the replacement is supported by evidence or explicit review

### Effect
- old item state becomes `superseded`
- new item becomes the active recall target
- recall should still expose the lineage when needed

## 8. Trust and provenance rules

Provenance constrains promotion.

### V1 policy
- `user`: trusted for episodic and core promotion
- `agent`: trusted for episodic and candidate generation, conditionally trusted for core promotion
- `subagent`: allowed into episodic/session memory, but requires stronger evidence before core promotion and may not directly enter hot memory
- `import`: trusted only for migration flows, not as a shortcut around review rules

## 9. Sanitization rules

Before promotion into core or AGENT hot memory, candidate text must be checked for:
- prompt injection phrases intended to alter agent control flow
- hidden or zero-width characters
- malformed metadata structures
- path-like or command-like content that should remain raw evidence rather than durable memory

Suspicious items should remain in episodic/session memory or require manual review.

## 10. Scoring model

Scoring is supportive, not sovereign. It helps rank candidates but does not replace policy.

V1 score components may include:
- recurrence
- distinct-day count
- explicit remember intent
- category confidence
- change-claim confidence
- provenance trust
- behavioral impact estimate

A high score alone must not bypass category, trust, or promotion rules.

## 11. Weekly review outputs

The weekly review should report:
- newly promoted core memories
- newly pinned hot memories
- archived items
- superseded items
- AGENT hot-memory items that show no recent activation
- unresolved high-score candidates still waiting for category or review

## 12. Success condition

The promotion system is working when:
- repeated useful facts rise naturally from raw logs into warm memory
- hot memory grows slowly and only through explicit pin/review policy
- stale facts can leave active circulation without being destroyed
- replacement facts supersede old ones cleanly
- the agent ends up with a small, reliable hot set and a larger, searchable warm layer instead of one undifferentiated memory pile
