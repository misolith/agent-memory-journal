# Glossary

## claim
A candidate statement about reality, behavior, policy, preference, capability, or constraint that may be worth remembering.

## normalized_claim
A comparison-friendly representation of a claim used for grouping repeated facts.

### V1 note
`normalized_claim` is **not yet fully specified for implementation**. This is a deliberate open issue and a technical risk.

The current direction is:
- lowercase text
- tokenize
- remove obvious punctuation
- remove stop words
- apply light lemmatization or stemming when practical
- compare via token-set similarity rather than exact string equality

### V1 policy boundary
Until the implementation is finalized, Rule A in promotion should be interpreted as:
- repeated claim detection is based on a normalization + similarity strategy,
- not raw string equality,
- and the exact method must be resolved in `docs/open_questions.md` before Phase B work starts.

## candidate
A memory item extracted from session or episodic sources that has not yet become stable core memory.

## session
A bounded execution scope for one active run, task, or multi-agent job.

### Session properties
- has a stable session identifier
- may contain contributions from agent and subagents
- has TTL tied to session lifecycle or explicit cleanup policy
- can produce promotion candidates when the same claim recurs across sessions or appears in episodic memory

## provenance
The declared origin of a memory item.

Allowed V1 values:
- `user`
- `agent`
- `subagent`
- `import`

## active
A memory item that is currently valid and eligible for normal recall.

## archived
A memory item retained for audit and possible restoration, but no longer considered active working memory.

## superseded
A memory item that has been replaced by a newer active item and should no longer be the default operational truth.

## supersedes
A directed relationship where a newer item replaces an older one without deleting history.

## pinned
A review-approved status that marks a core memory item as eligible for inclusion in `AGENT.md`.

## AGENT.md
The hot-memory surface that is always loaded into agent context. Small, derived, and tightly constrained.

## core memory
Warm durable memory organized by category and recalled on demand.

## episodic memory
Cold append-oriented log of raw observations, daily notes, and source events.

## session memory
Short-term memory specific to one active execution context. Intended for transient coordination, not default long-term retention.

## distinct day
A unique calendar date represented in episodic memory sources.

## distinct session
A unique session identifier in session-scoped memory. Distinct sessions are not the same as repeated entries in one session.

## stable id
A durable identifier attached to a promoted memory item so that archive and supersedes relationships can be tracked over time.
