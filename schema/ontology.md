# Ontology: The Epistemic Control Layer

> AI proposes; counsel disposes.

This document is the intellectual heart of the repository. It explains *why* the graph schema is structured the way it is. The schema is not decorative infrastructure. It is an **epistemic control layer**: a deliberate separation of evidence, interpretation, finding, and decision that makes AI-assisted legal review auditable, reviewable, and durable across model upgrades.

---

## Why source text is not a claim

In ordinary retrieval-augmented generation, source passages and generated answers are easily conflated. A passage is retrieved, a summary is generated, and the user sees one answer.

In high-stakes review, that conflation is unacceptable.

The `SourceSpan` is preserved as an addressable, immutable object with a stable `span_id`, `char_start`, `char_end`, and `text_hash`. The span is the **evidence**. It is what the contract actually says.

A `Claim` is *about* the span. It is an AI-generated interpretation. It can be wrong. It can be revised. It can be withdrawn. The span cannot.

Separating these objects means:

- Two different models, two months apart, can produce two different claims about the same span without corrupting the evidence.
- A reviewer can re-read the underlying text without trusting any model output.
- The provenance from claim back to source is always one edge away.

---

## Why claims are not decisions

A `Claim` is what the model proposed. A `ReviewDecision` is what a human authorized.

In ordinary RAG, a generated answer is presented as if it were a conclusion. In legal and compliance work, that elides the authority boundary: the model does not have authority to conclude anything.

By making `Claim` and `ReviewDecision` distinct nodes:

- The graph records that a claim existed.
- The graph records who reviewed it.
- The graph records what authority level they hold.
- The graph records the rationale.

This is the **human authority boundary**, made explicit and queryable.

---

## Why risk findings are not decisions

A `RiskFinding` aggregates one or more claims into a reviewable issue. It is the unit of work a lawyer sees in an exception report.

But the finding's `proposed_status` is not a decision. It is the model's framing of the issue. The decision belongs to the human, on a separate `ReviewDecision` node.

This three-layer separation — claim, finding, decision — prevents two failure modes:

1. **Premature closure**, where AI output gets treated as a resolved issue.
2. **Lost dissent**, where an early reviewer's disagreement gets silently overwritten by a later one.

---

## Why tensions are first-class objects

The relationships `TENSIONS_WITH`, `COMPLIES_WITH`, and `CREATES_LIABILITY_UNDER` are not metadata on a finding. They are graph edges between a `Claim` and a `Policy`.

Tensions are first-class objects because:

- A single claim can simultaneously tension with one policy and comply with another. Both facts matter.
- Tensions can be queried, counted, and reported on independently of any single finding.
- The same tension can be re-examined under a new policy version, producing a new claim against the new policy without losing the old relationship.

In short, **disagreement has structure**. The graph preserves that structure.

---

## Why human review is non-destructive

Real legal review involves disagreement, escalation, and revision over time. An associate may approve a concession; a senior counsel may later escalate it; the general counsel may later reject the escalation.

If the system overwrote prior decisions, the institutional memory of *why* the contract ended up where it did would be lost.

Instead, each new `ReviewDecision` is a new node. It is linked to its predecessor via `SUPERSEDES`. The complete chain is preserved. This is a **persistent curation graph**: a model-independent review history.

---

## Why model runs must be preserved

A `ModelRun` records:

- which model produced the claim,
- which version of the model,
- which prompt version,
- when it ran,
- in what extraction mode.

This is preserved because:

- Models change. The same prompt against a newer model may produce different claims. The graph must let auditors compare.
- Compliance reviews may require demonstrating that a specific model version was in use at a specific time.
- Withdrawing or superseding a claim after a model upgrade is impossible to reason about without the model run record.

The model run is the **AI provenance object**, parallel to the human `Expert` object on the review side.

---

## Why this survives model upgrades

Because the schema separates source span, claim, finding, and decision — and because model runs are recorded — the graph is **stable across model upgrades**.

When a new model version produces new claims:

- The same source spans are reused.
- The same policies are reused.
- The same prior decisions stand.
- New claims, with a new `ModelRun`, attach to the same evidence.

The institutional record does not need to be rebuilt. It accumulates.

This is the central architectural commitment: **auditable semantic extraction** that does not collapse when the model behind it is replaced.

---

## How this differs from ordinary RAG

Ordinary RAG retrieves passages and generates answers. It is built for *answering questions*. It assumes the user is the authority and the model is the assistant.

In high-stakes legal review, the relationships are different:

- The contract is the authority.
- Counsel is the authority over interpretation.
- The model is a candidate-generator, not a decision-maker.

The graph encodes this. It refuses to treat generated text as a durable institutional artifact. It treats AI output as **proposals**, evidence as **evidence**, and human review as **the authority that resolves them**.

For a fuller comparison, see [`../docs/why_not_just_rag.md`](../docs/why_not_just_rag.md).

---

## Why the graph is an epistemic control layer

The repository title uses the phrase *epistemic control layer* deliberately.

"Epistemic" because the graph governs what counts as known, by whom, and on what basis.

"Control" because the graph structurally prevents AI output from becoming authoritative without human legal review.

"Layer" because it is positioned between the source text and the final exception report, mediating the path from raw contract to actionable review artifact.

The graph is not there to look impressive. It exists because:

- Source-span-grounded claims require it.
- Model-independent review history requires it.
- Durable policy tensions require it.
- A human authority boundary requires it.

A flat document store or a chat log cannot do this. A pile of generated summaries cannot do this. A graph with the right node and edge vocabulary can.

That is the thesis of this reference model.

---

## A note on hallucination

This system does not eliminate hallucination. LLMs will still produce incorrect claims.

What this system does is **contain hallucination risk**:

- Hallucinated claims still record their `ModelRun`, so they can be located and audited.
- Hallucinated claims must still be `GROUNDED_IN` a `SourceSpan`, exposing groundless claims as schema violations.
- Hallucinated claims never become decisions without a `ReviewDecision` from a human expert.
- Hallucinated claims that pass into a `RiskFinding` are visible in the exception report, where counsel reviews them before any action is taken.

The model can be wrong. The graph makes wrongness reviewable. The lawyer holds authority. That is the design.
