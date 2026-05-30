# Graph Schema (Human-Readable)

This document describes the graph schema for the Human-in-the-Loop GraphRAG legal reference model. It is intended for both technical readers (engineers, data architects, AI governance leads) and legal/compliance readers (counsel, contract managers, regulators).

The corresponding machine-readable schema lives in [`graph_schema.json`](./graph_schema.json).

---

## Design Principles

The schema is built around four principles:

1. **Evidence is not interpretation.** Source text is preserved separately from any AI claim about it.
2. **Interpretation is not authority.** AI-proposed claims and risk findings are separate from human review decisions.
3. **Review is non-destructive.** Decisions are never overwritten. New decisions reference and supersede prior decisions.
4. **Model behavior is provenance.** Every claim records the model run that produced it, so semantic outputs remain traceable across model upgrades.

---

## Node Labels

### `Document`

An uploaded, baseline, or vendor-supplied legal document.

| Property | Required | Notes |
|---|---|---|
| `document_id` | yes | Stable identifier |
| `title` | yes | Human-readable title |
| `document_type` | yes | One of: `baseline_msa`, `company_policy`, `vendor_draft`, `amendment`, `other` |
| `version` | yes | Document version string |
| `effective_date` | yes | ISO date |
| `source_system` | yes | Where the document originated (e.g., CLM, DMS) |
| `created_at` | yes | ISO datetime |

### `SourceSpan`

Addressable text inside a document. This is the **evidence object**. It must remain stable and addressable across model runs.

| Property | Required | Notes |
|---|---|---|
| `span_id` | yes | Stable identifier |
| `document_id` | yes | Parent document |
| `section_label` | yes | E.g., "§5 Indemnification" |
| `char_start` | yes | Inclusive offset |
| `char_end` | yes | Exclusive offset |
| `text` | yes | Verbatim text |
| `text_hash` | yes | Hash for integrity checks |

### `Clause`

A legally meaningful clause derived from one or more source spans.

| Property | Required | Notes |
|---|---|---|
| `clause_id` | yes | Stable identifier |
| `clause_type` | yes | E.g., `indemnification`, `limitation_of_liability` |
| `normalized_title` | yes | Canonical title |
| `jurisdiction` | yes | Governing jurisdiction |
| `source_status` | yes | `baseline`, `vendor_proposed`, `negotiated`, `executed` |

### `Policy`

A company baseline rule or external legal/compliance standard.

| Property | Required | Notes |
|---|---|---|
| `policy_id` | yes | Stable identifier |
| `policy_name` | yes | Human-readable name |
| `policy_type` | yes | E.g., `indemnification`, `payment_terms` |
| `version` | yes | Policy version |
| `rule_text` | yes | The actual rule |
| `risk_tolerance` | yes | `low`, `medium`, `high` |
| `owner` | yes | Owning function (Legal, Compliance, Procurement, etc.) |
| `effective_date` | yes | ISO date |

### `Claim`

An **AI-proposed** semantic interpretation. A claim is not truth. It is an interpretation proposed by a model run and grounded in a source span.

| Property | Required | Notes |
|---|---|---|
| `claim_id` | yes | Stable identifier |
| `claim_text` | yes | The interpretation statement |
| `claim_type` | yes | E.g., `policy_tension`, `liability_creation` |
| `confidence` | yes | 0.0–1.0 |
| `status` | yes | `proposed`, `superseded`, `withdrawn` |
| `created_at` | yes | ISO datetime |

### `RiskFinding`

A proposed review issue created from one or more claims.

| Property | Required | Notes |
|---|---|---|
| `finding_id` | yes | Stable identifier |
| `finding_type` | yes | E.g., `indemnification_narrowed` |
| `severity` | yes | `low`, `medium`, `high`, `critical` |
| `finding_summary` | yes | Short description |
| `proposed_status` | yes | `proposed`, `approved_concession`, `rejected`, `escalated` |
| `created_at` | yes | ISO datetime |
| `reportable` | yes | Boolean, whether the finding appears in the exception report |

### `ReviewDecision`

A **human** lawyer or compliance reviewer's decision.

| Property | Required | Notes |
|---|---|---|
| `decision_id` | yes | Stable identifier |
| `decision` | yes | `approved_concession`, `rejected`, `escalated` |
| `rationale` | yes | Human-authored rationale |
| `decided_at` | yes | ISO datetime |
| `authority_level` | yes | E.g., `senior_counsel`, `general_counsel` |

Decisions are **never overwritten**. A new decision is created and linked via `SUPERSEDES_DECISION` to the prior one.

### `Expert`

A reviewing lawyer or compliance expert.

| Property | Required | Notes |
|---|---|---|
| `expert_id` | yes | Stable identifier |
| `name` | yes | Reviewer name |
| `role` | yes | E.g., "Senior Counsel" |
| `bar_jurisdiction` | yes | E.g., "NY" |
| `organization` | yes | Reviewer's firm or in-house team |

### `ModelRun`

A single AI extraction event. Preserves provenance across model upgrades.

| Property | Required | Notes |
|---|---|---|
| `model_run_id` | yes | Stable identifier |
| `model_name` | yes | E.g., `stubbed-llm` |
| `model_version` | yes | E.g., `v0.1-reference` |
| `prompt_version` | yes | E.g., `prompt-contract-risk-001` |
| `run_timestamp` | yes | ISO datetime |
| `extraction_mode` | yes | `stubbed`, `zero_shot`, `few_shot`, `fine_tuned`, `deterministic` |

---

## Relationships

### Provenance and structure

- `(Document)-[:CONTAINS]->(SourceSpan)`
- `(Clause)-[:HAS_SPAN]->(SourceSpan)`
- `(Claim)-[:GROUNDED_IN]->(SourceSpan)`
- `(Claim)-[:EXTRACTED_BY]->(ModelRun)`
- `(RiskFinding)-[:BASED_ON]->(Claim)`

### Legal and compliance semantics

- `(Claim)-[:ASSERTS]->(Clause)`
- `(Claim)-[:TENSIONS_WITH]->(Policy)`
- `(Claim)-[:COMPLIES_WITH]->(Policy)`
- `(Claim)-[:CREATES_LIABILITY_UNDER]->(Policy)`
- `(Claim)-[:AMENDS_CLAUSE]->(Clause)`

### Human review

- `(ReviewDecision)-[:REVIEWS]->(RiskFinding)`
- `(ReviewDecision)-[:MADE_BY]->(Expert)`
- `(ReviewDecision)-[:SUPERSEDES]->(ReviewDecision)`

### Policy and version control

- `(Policy)-[:SUPERSEDES]->(Policy)`

---

## Validation Rules

1. Every `Claim` must be `GROUNDED_IN` at least one `SourceSpan`.
2. Every `Claim` must be `EXTRACTED_BY` exactly one `ModelRun`.
3. Every `RiskFinding` must be `BASED_ON` at least one `Claim`.
4. `ReviewDecision` nodes must never be deleted. A new decision is created and `SUPERSEDES` the previous.
5. `Policy` upgrades must never be deleted. A new policy is created and `SUPERSEDES` the prior version.
6. Claim status transitions are constrained to `proposed -> superseded` and `proposed -> withdrawn`.
7. A `RiskFinding` is `reportable` only if it has complete provenance: at least one `Claim`, one `SourceSpan`, one `Policy`, and one `ModelRun`.

These rules are intentionally simple. They are designed to make the audit trail legible to lawyers, auditors, and engineers alike.
