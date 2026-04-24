# Scope Decision Document

## Purpose

This document fixes the scope of `agent-memory-journal` before further implementation. The repository is not being built as a generic note-taking CLI or a team knowledge base. It is being reshaped into a practical long-term memory system for an OpenCode / Claude Code / OpenClaw style agent.

## Primary target

### In scope
- One agent identity
- One repository or operator workspace at a time
- One primary human/operator relationship
- Long-term memory that survives sessions
- Short-term session memory that can be promoted into long-term memory

### Out of scope for V1
- Multi-tenant memory
- Shared team memory as the primary model
- Generalized enterprise knowledge management
- Autonomous free-form summarization as a source of truth
- Unbounded hot-context memory

## Memory model

The system is explicitly three-tiered:

1. **Hot memory**
   - always loaded into agent context
   - tiny, curated, behavior-shaping
   - stored in `AGENT.md`

2. **Warm memory**
   - not always loaded
   - recalled on demand
   - structured by category
   - stored in `core/`

3. **Cold memory**
   - append-oriented episodic history
   - auditable, not routinely loaded
   - stored in `episodic/`

The repository will no longer treat all memory files as equivalent.

## What counts as important

V1 uses five durable memory categories:
- `decision`
- `constraint`
- `gotcha`
- `preference`
- `capability`

These categories are mandatory for warm/core memory. A memory item without a category is not eligible for stable promotion.

### Category intent
- **decision**: a settled choice that should steer future behavior
- **constraint**: a rule, boundary, prohibition, or non-negotiable condition
- **gotcha**: a failure mode, trap, edge case, or subtle operational hazard
- **preference**: a stable user or agent preference that changes how work should be done
- **capability**: a stable statement about what the system can now do, cannot do, or no longer does

## What is forgotten

Forgetting is modeled as state transition, not destructive deletion.

Allowed states:
- `active`
- `archived`
- `superseded`

### Rules
- Episodic memory is retained as audit history unless explicitly pruned by a separate retention policy.
- Core memory can move from `active` to `archived` after inactivity.
- Core memory can move from `active` to `superseded` when a newer claim replaces it.
- AGENT hot memory is regenerated from active pinned core memory rather than edited as an immortal notebook.

## Threat model and write permissions

Each memory item must carry provenance.

Allowed provenance values in V1:
- `user`
- `agent`
- `subagent`
- `import`

### Write policy
- `user` may write episodic memory directly
- `agent` may write episodic memory directly
- `subagent` may write episodic memory, but its writes are lower trust for hot-memory promotion
- `import` is reserved for migrations and batch ingestion

### Promotion policy
- episodic to core promotion may be automated if policy rules are met
- core to AGENT hot-memory promotion is never wide open
- subagent-origin memory must not reach `AGENT.md` directly without either repeated corroboration or explicit review/pin approval

## Operational doctrine

This system optimizes for:
- low hot-context cost
- explicit promotion instead of accidental accumulation
- auditability
- reversible forgetting
- evidence-backed long-term memory

It does **not** optimize for:
- storing everything forever in the hot set
- treating every daily note as durable truth
- generic compatibility with every possible agent architecture

## Success criteria for scope

The scope is correct when all of the following are true:
- `AGENT.md` remains small enough to load all the time and stays within the hard limit defined in `docs/architecture.md`
- `core/` is the main durable working memory layer
- `episodic/` remains useful as raw source material, not as the agent's primary memory surface
- promotion requires either repeated evidence or explicit human/agent intent
- the repository design stays centered on one agent + one operator context rather than drifting into generic knowledge tooling
