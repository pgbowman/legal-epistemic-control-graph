# Why Not Just RAG?

Retrieval-augmented generation is genuinely useful. It is also insufficient for high-stakes review.

The short version:

> RAG answers questions. This model preserves reviewable institutional memory.

The longer version is below.

---

## What RAG Is Built For

A typical RAG pipeline:

1. Embeds a corpus.
2. Retrieves passages relevant to a query.
3. Generates an answer grounded in those passages.
4. Returns the answer to the user.

This is excellent when:

- The user holds final authority over the answer.
- The answer is needed once, in the moment.
- No durable institutional record of the answer is required.
- The same answer would be acceptable to regenerate later.

Legal and compliance review does not meet any of those conditions.

---

## Where RAG Falls Short for Legal Review

| Ordinary RAG | Epistemic Control Graph |
|---|---|
| retrieves passages | preserves addressable source spans |
| generates answers | proposes claims |
| logs prompts | records model runs |
| summarizes risk | creates reviewable findings |
| overwrites outputs | preserves decision history |
| user trusts answer | expert reviews claim |

Each row is the same underlying disagreement: **RAG produces ephemeral answers; legal review requires durable artifacts.**

---

## Five Concrete Failure Modes

**1. Source-text drift.** In RAG, retrieved passages are not stable artifacts in the system. They are a side-effect of the retrieval index. If the index is rebuilt, the same query may return different passages, and the generated answer may differ. Counsel cannot rely on this.

In this reference model, `SourceSpan` is a first-class node with stable `span_id`, character offsets, and a text hash. It is the evidence. It does not move when the index rebuilds.

**2. Collapsed authority.** RAG presents a generated answer as a conclusion. There is no structural distinction between "what the model proposed" and "what counsel decided". In legal review, that distinction is the whole point.

This model splits them into `Claim` (AI proposal) and `ReviewDecision` (human authority), with a `RiskFinding` mediating between them.

**3. Lost history.** RAG outputs are typically regenerated on demand. If a lawyer reviewed last quarter's answer and recorded a rationale, that rationale lives outside the RAG system. If the answer is regenerated next quarter against a new model, the rationale and the new answer are orphaned from each other.

This model records `ReviewDecision` nodes that persist independently of any single model run, and `ModelRun` provenance that lets future readers correlate old decisions with the models that produced the claims they reviewed.

**4. Opaque model upgrades.** When the LLM behind a RAG system is upgraded, the old answers are not re-evaluated; they simply disappear. Auditors cannot ask "did the prior model produce a riskier interpretation that someone signed off on?".

In this model, `ModelRun` is a node. Old claims and the model runs that produced them are preserved. A new model run produces new claims attached to the same source spans, and the graph supports comparison.

**5. No first-class disagreement.** RAG does not represent disagreement between an AI proposal and a baseline rule. It generates prose. If the prose mentions a conflict, the conflict is text, not data.

In this model, `TENSIONS_WITH`, `COMPLIES_WITH`, and `CREATES_LIABILITY_UNDER` are graph edges between `Claim` and `Policy`. Disagreement is structured, queryable, and reportable.

---

## When RAG Is Still the Right Tool

RAG is not the enemy. For:

- internal knowledge-base Q&A,
- code-search assistants,
- documentation chat,
- onboarding helpers,

RAG is perfectly fine.

The argument here is narrower: when the AI is being used to produce **interpretations** of **high-stakes text** that **humans must review and decide on**, ordinary RAG is the wrong shape of system. The shape this repository sketches is closer to the right shape.

---

## What an "Epistemic Control Graph" Adds

Ordinary RAG is optimized for **answer generation**. This reference model is optimized for **accountable interpretation**.

The key difference is not that this system uses a graph. The key difference is that the graph records the institutional status of each assertion:

- evidence,
- proposed interpretation,
- reviewable risk,
- human decision,
- superseded decision,
- policy version,
- model run.

A vector database can retrieve passages. It cannot, by itself, represent institutional authority.

To put it in one sentence:

> The graph preserves the difference between evidence, interpretation, risk, and authority — across time, across model versions, and across human reviewers.

That is what makes the resulting workflow auditable, reviewable, and durable.
