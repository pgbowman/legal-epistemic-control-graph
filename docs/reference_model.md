# The Reference Model

This document describes the reference model in more depth than the README. It is intended for engineering directors, legal-tech CTOs, AI governance leads, and senior knowledge-systems people who want to understand *why* this architecture is shaped the way it is, and how to extend it.

---

## Core Entities

The model is built around nine node labels and a constrained edge vocabulary. They are documented in [`../schema/graph_schema.md`](../schema/graph_schema.md). Here, the focus is on the **roles** these entities play, not their fields.

| Entity | Role |
|---|---|
| `Document` | The container. An MSA template, a policy, a vendor draft. |
| `SourceSpan` | The evidence. Addressable, immutable, hashed text. |
| `Clause` | The legal unit. One or more spans, normalized for type. |
| `Policy` | The baseline rule, with its own versioning and ownership. |
| `Claim` | An AI-proposed semantic interpretation. Never authoritative. |
| `RiskFinding` | A reviewable issue, aggregated from one or more claims. |
| `ReviewDecision` | The human authority record. Non-destructive. |
| `Expert` | The reviewer. Has authority level and bar jurisdiction. |
| `ModelRun` | The AI provenance object. Parallel to `Expert`. |

The graph is small on purpose. Every node label exists because removing it would collapse a distinction the architecture is built to preserve.

---

## Lifecycle of a Finding

A finding moves through these stages:

1. **Ingest.** The baseline MSA, the policy, and the vendor draft are loaded. Each document becomes a `Document` with `SourceSpan` children, and clauses are normalized.
2. **Model run.** A `ModelRun` node is created representing the AI extraction event.
3. **Claim generation.** For each span the model interprets, a `Claim` is created and connected to the span via `GROUNDED_IN` and to the model run via `EXTRACTED_BY`.
4. **Policy linkage.** Each claim is connected to the relevant policy via `TENSIONS_WITH`, `COMPLIES_WITH`, or `CREATES_LIABILITY_UNDER`.
5. **Clause linkage.** Where the claim asserts or amends a clause, `ASSERTS` or `AMENDS_CLAUSE` edges are created.
6. **Risk finding.** One or more claims are bundled into a `RiskFinding`, connected via `BASED_ON`.
7. **Exception report.** Reportable findings are rendered into a PDF for counsel.
8. **Review decision.** A reviewer records a `ReviewDecision`, connected to the finding and to the expert. If a prior decision exists, the new decision `SUPERSEDES` it.

At no point is any prior object overwritten. The graph accumulates.

---

## Status Transitions

### Claim status

- `proposed` → `superseded` (a later run produced a better-grounded claim)
- `proposed` → `withdrawn` (the model run is later judged unreliable)

A claim never becomes `decided`. Decisions live on `ReviewDecision` nodes.

### RiskFinding proposed_status

- `proposed` (initial)
- `approved_concession` | `rejected` | `escalated` (reflecting the latest review decision)

The finding's `proposed_status` is a denormalized convenience, not the authoritative record. The authoritative record is the chain of `ReviewDecision` nodes.

### ReviewDecision

A `ReviewDecision` is **immutable**. To change a decision, create a new `ReviewDecision` and link it via `SUPERSEDES` to the prior one.

---

## Graph Invariants

The graph enforces these invariants. They are checked by `src/evaluate.py`.

1. Every `Claim` is `GROUNDED_IN` at least one `SourceSpan`.
2. Every `Claim` is `EXTRACTED_BY` exactly one `ModelRun`.
3. Every reportable `RiskFinding` is `BASED_ON` at least one `Claim`.
4. Every reportable `RiskFinding` has at least one `Policy` reachable through its claims.
5. No `ReviewDecision` is ever deleted. Newer decisions create `SUPERSEDES` edges.
6. No `Policy` is ever deleted. New versions create `SUPERSEDES` edges.

These invariants are deliberately easy to state and easy to query. They are the contract between the engineering layer and the legal review process.

---

## Extending to Other Domains

The same architecture applies wherever LLMs are used to propose interpretations of high-stakes text that humans must review. The substitutions are mechanical:

| Domain | Document | Source span | Claim | Finding | Decision-maker |
|---|---|---|---|---|---|
| Contract review | MSA / vendor draft | clause text | policy tension | risk finding | counsel |
| Clinical research review | protocol / consent form | passage | safety / ethical concern | review finding | IRB member |
| Insurance underwriting | application / appraisal | claim line | risk indicator | underwriting flag | underwriter |
| Regulatory filings review | 10-K / 10-Q | disclosure passage | disclosure gap | filing exception | securities counsel |

The only real domain work is enumerating the `Policy` set, the `Clause`/section taxonomy, and the `RiskFinding` finding types. Everything else follows.

---

## Why This Architecture Supports Human-in-the-Loop Review

Three properties make this architecture HITL-native rather than HITL-bolted-on:

1. **Authority boundary.** AI output reaches `Claim` and `RiskFinding`, but never `ReviewDecision`. The handoff is structurally explicit, not enforced by a process document.
2. **Non-destructive history.** Disagreement, escalation, and revision are preserved as a chain rather than overwritten. The graph reflects the actual social structure of legal review.
3. **Model independence.** Because `ModelRun` is its own node and claims are typed and grounded, replacing the model does not invalidate prior decisions or evidence. Two model versions can coexist in the graph.

These three properties are why the graph is described as an *epistemic control layer*. They are what a flat document store, a chat log, or a vector index cannot provide.
