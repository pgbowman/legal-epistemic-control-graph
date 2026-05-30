# Graph Contract

This document defines the minimum guarantees expected of the curation graph. Other documents in this repository describe how the graph is shaped; this document describes what it must, by design, preserve.

Each guarantee below is enforced either statically (by the schema) or dynamically (by `src/evaluate.py`).

---

## Evidence Guarantee

Every AI-proposed claim must be grounded in an addressable source span.

- Enforced by: schema requirement that `Claim` connects to a `SourceSpan` via `GROUNDED_IN`.
- Verified by: `evaluate.py` rejects any reportable finding whose claims lack a span.
- Implication: a hallucinated claim with no underlying text fails evaluation and cannot enter the exception report.

---

## Model Provenance Guarantee

Every AI-proposed claim must be linked to the model run that produced it.

- Enforced by: schema requirement that `Claim` connects to exactly one `ModelRun` via `EXTRACTED_BY`.
- Verified by: `evaluate.py` rejects any finding whose claims lack a model run.
- Implication: replacing the model later does not erase the prior interpretations; they remain traceable to the model that produced them.

---

## Authority Boundary Guarantee

No AI-generated object is treated as a human decision.

- Enforced by: separate node labels (`Claim`, `RiskFinding`) for AI output and `ReviewDecision` for human authority.
- Verified by: `evaluate.py` and the schema; `RiskFinding.proposed_status` is never `decided`.
- Implication: the model can propose, but only an `Expert` recorded on a `ReviewDecision` can decide.

---

## Non-Destructive Review Guarantee

Human review decisions are appended as new nodes. They are not represented by overwriting the finding.

- Enforced by: `src.curate` always creates a new `ReviewDecision` and, if a prior decision exists, links it via `SUPERSEDES`.
- Verified by: `evaluate.py` detects orphan decisions and rejects multiple current (non-superseded) decisions on the same finding.
- Implication: the chain of decisions on a finding — including reversals and escalations — is queryable indefinitely.

---

## Version Survival Guarantee

The graph must remain meaningful after model upgrades, policy revisions, or new review decisions.

- Enforced by: `ModelRun` and `Policy` are first-class nodes with their own version fields; new versions create `SUPERSEDES` edges to prior versions.
- Verified by: ingest writes `Policy SUPERSEDES Policy` edges; `evaluate.py` requires every `Policy` to have a version.
- Implication: a finding raised against `POL-PAY-001 v3.1` remains coherent even after a `POL-PAY-001 v4.0` is added later, because the historical version is preserved and linked.

---

## Why a Contract, Not a Specification

These guarantees are deliberately phrased as a *contract*, not a specification. They are commitments the graph makes to its readers — reviewers, auditors, regulators — about what the structure preserves.

A specification answers *how* the system is built. A contract answers *what you can rely on regardless of how it is built.* The contract is the part that survives implementation changes.
