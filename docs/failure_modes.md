# Failure Modes

This reference model does not assume the AI is correct. It assumes the AI will sometimes be wrong, and that policies will change, and that reviewers will disagree with each other and with their past selves. The design's job is to contain those failures.

This document lists the failure modes that motivated the architecture and explains how the graph contains each one.

---

## Possible Failures

| Failure | How the model contains it |
|---|---|
| Hallucinated claim | Must be grounded in a `SourceSpan` via `GROUNDED_IN`, or evaluation fails. A claim with no underlying text cannot enter the exception report. |
| Wrong policy mapping | Visible as a `Claim`-to-`Policy` edge. Reviewable by counsel; can be rejected without disturbing the underlying source span or the model run that produced the claim. |
| Model upgrade changes the result | The old `ModelRun` and its `Claim` nodes remain in the graph. A new model run creates new claims attached to the same source spans; the prior interpretations stay reviewable. |
| Lawyer changes their decision | A new `ReviewDecision` is created and linked via `SUPERSEDES` to the prior one. The prior decision and its rationale remain queryable. |
| Two reviewers disagree | Both decisions are preserved; the chain of `SUPERSEDES` edges records who superseded whom and when. |
| Policy changes later | The new `Policy` is created and `SUPERSEDES` the prior version. Historical findings remain linked to the policy version in effect at the time. |
| Overbroad report summary | Each finding detail page in the exception report includes the source excerpt, the AI claim text, the policy rule text, and the provenance trail. Counsel reviews the grounded artifact, not the summary. |
| Confidence-only filtering | `Claim.confidence` is recorded but is not the basis for inclusion. Reportability is structural: a finding must have full provenance, not merely high confidence. |
| Silent loss of evidence | `SourceSpan.text_hash` is required. A span with an empty hash fails evaluation. |
| Re-running review against fresh policy | Because policies are versioned, a re-run produces a new claim against the new policy version without erasing the historical record. |

---

## Failures the Architecture Does Not Address

The reference model is honest about what it does not do:

- **Detecting that the AI is wrong.** The architecture makes wrongness reviewable; it does not detect it. That is counsel's job.
- **Guaranteeing reviewer competence.** A `ReviewDecision` recorded by an unqualified reviewer is still a decision. The `authority_level` and `bar_jurisdiction` fields on `Expert` let downstream queries filter on competence, but they do not enforce it.
- **Stopping bad-faith review.** A reviewer who deliberately approves a concession against policy will produce a `ReviewDecision` with a misleading rationale. The graph preserves the record; it does not adjudicate motives.
- **Replacing legal judgment.** The exception report is a working artifact, not a conclusion. The footer says so on every page.

These are real failure modes. They are out of scope for the graph. Naming them explicitly is part of the architecture's honesty.

---

## Why This Matters

A system that overclaims its protections is more dangerous than a system that admits its limits. The point of this reference model is not to argue that AI-assisted legal review is safe. The point is to argue that, when AI is used, the architecture should make every interpretation reviewable, every decision auditable, and every model run traceable — and should resist the temptation to collapse all of those into a single generated answer.

That is the failure mode this repository is designed to prevent.
