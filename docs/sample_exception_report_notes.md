# Sample Exception Report Notes

This document explains what the generated PDF at `reports/exception_report.pdf` is meant to show, and how a lawyer would use it.

---

## What the Report Is

The exception report is the **artifact** of an AI-assisted contract review. It is the document a reviewer would print, mark up, and return.

It is intentionally conservative in style — black on white, sans-serif, no logos, no charts — because it is a working legal artifact, not marketing collateral.

The report is also the visible end of the epistemic control graph. Every field in it can be traced back to a node and edge in the graph:

| Report section | Backing graph object(s) |
|---|---|
| Contract metadata | `Document` (vendor draft) |
| Baseline policy metadata | `Document` (policy), `Policy` |
| Model run metadata | `ModelRun` |
| Exception table | `RiskFinding` rows |
| Source span excerpt | `SourceSpan` |
| AI-proposed claim | `Claim`, with `GROUNDED_IN` and `EXTRACTED_BY` |
| Policy tension | `Policy`, with `TENSIONS_WITH` or similar |
| Provenance trail | the path `RiskFinding -> Claim -> SourceSpan / ModelRun / Policy` |
| Human review checklist | the *future* `ReviewDecision` node, to be recorded via `src.curate` |

---

## How a Lawyer Would Use It

1. **Skim the executive summary.** Counts by severity. Reviewer instructions.
2. **Read the exception table.** One row per reportable finding, with severity and a summary.
3. **For each row, open the finding detail page.**
   - Read the source span excerpt. This is what the contract actually says.
   - Read the AI-proposed claim. This is what the model thinks it means.
   - Read the policy tension. This is the baseline rule the claim conflicts with.
   - Decide.
4. **Record the decision** on the checklist (Approved Concession / Rejected / Escalated), sign, and date.
5. The recorded decision is then entered into the graph via `python -m src.curate ...`, which creates a `ReviewDecision` node and links it to the finding. If a prior decision exists, the new one supersedes it non-destructively.

---

## What the Report Is *Not*

- Not legal advice.
- Not a contract redline.
- Not a substitute for the underlying contract.
- Not a final document.

The footer on every page makes this explicit:

> Review artifact only. Not legal advice. AI-proposed findings require counsel review.

---

## Design Choices

- **One reportable finding per detail page.** Counsel can annotate without flipping pages.
- **Span excerpt before claim.** The evidence is shown first; the AI interpretation is shown second. This ordering reflects the authority order: source text is authoritative, the AI claim is not.
- **Checklist instead of free-text decision.** The three decision values mirror the schema's `ReviewDecision.decision` enum. A reviewer cannot record an out-of-schema decision.
- **Signature and date.** Even when the system records the decision in the graph, the print artifact retains a signature line. Legal review still relies on signed paper in many organizations and jurisdictions.
- **Provenance trail listed explicitly.** The relationships (`GROUNDED_IN`, `EXTRACTED_BY`, `TENSIONS_WITH`, `BASED_ON`) are spelled out so an auditor reading the PDF alone can reconstruct the graph path.
