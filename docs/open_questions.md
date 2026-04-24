# Open Questions

These questions must be resolved before Phase B implementation work starts.

## 1. What exactly is `normalized_claim`?

Status: Open

Why it matters:
- Rule A depends on repeated-claim detection.
- If normalization stays too literal, paraphrases will not cluster.
- If normalization becomes too fuzzy, unrelated claims may merge.

Options under consideration:
1. lowercase + punctuation stripping + stop-word removal + sorted token set
2. light stemming/lemmatization + token-set Jaccard similarity
3. BM25-assisted candidate grouping
4. embeddings-assisted grouping later, but not as V1 prerequisite

Required decision:
- define the exact V1 method
- define threshold(s)
- define failure mode and review fallback

## 2. What is a session exactly?

Status: Open

Why it matters:
- promotion rules refer to distinct sessions
- architecture includes `sessions/`
- without lifecycle rules, session memory will drift into another cold pile

Questions to answer:
- what creates a session id?
- does one interactive thread equal one session?
- do subagents inherit parent session id or get child ids?
- when does session TTL expire?
- what cleanup mechanism removes expired sessions?

Required decision:
- define session ownership, lifecycle, TTL, and cleanup policy

## 3. How are stable ids generated?

Status: Open

Why it matters:
- `supersedes` depends on durable ids
- archive and lineage need stable references
- naive UUID-only generation weakens deterministic migration and dedupe behavior

Options under consideration:
1. content hash
2. UUIDv7
3. content hash + monotonic suffix
4. category-prefixed deterministic id

Required decision:
- define V1 id scheme
- define collision behavior
- define whether edited text keeps or replaces id

## 4. What are the concrete sanitization patterns?

Status: Open

Why it matters:
- promotion hygiene is too vague without explicit examples
- AGENT.md is a control-adjacent file and must resist prompt-injection-like payloads

Minimum V1 deliverable:
- a concrete list of blocked or review-required patterns, for example:
  - `ignore previous instructions`
  - `system:` at line start in suspicious contexts
  - `developer:` at line start in suspicious contexts
  - zero-width characters
  - invisible control characters
  - fenced code blocks containing shell commands presented as memory facts
  - prompt-like role headers
  - malformed frontmatter or metadata injection

Required decision:
- define the V1 blacklist/review list
- define whether a match blocks promotion or downgrades to manual review

## 5. Should the AGENT hot-memory limit be enforced by characters or tokens first?

Status: Open

Why it matters:
- architecture currently states a V1 character limit
- token limit is conceptually better for prompt cost
- character limit is easier to ship first

Required decision:
- confirm V1 character cap as implementation-first choice, or switch immediately to token-aware validation

## Release gate

Phase B must not start until every question above is either:
- resolved in this file, or
- explicitly deferred with a documented reason and fallback behavior.
