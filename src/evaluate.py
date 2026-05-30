"""Evaluate the integrity of the reference graph.

This is the governance check. It enforces the architectural invariants the
schema and ontology describe, but at the level of the live graph rather than
the JSON sample data. The static schema is checked separately by `src.validate`.

Checks performed:

  Provenance
    * every reportable RiskFinding has at least one Claim
    * every reportable RiskFinding has at least one SourceSpan (via Claim)
    * every reportable RiskFinding has at least one Policy (via Claim)
    * every reportable RiskFinding has at least one ModelRun (via Claim)
    * every reportable RiskFinding has a proposed_status and reportable == true

  Claim integrity
    * every Claim's status is one of: proposed, superseded, withdrawn
    * every Claim's confidence is between 0.0 and 1.0

  Evidence integrity
    * every SourceSpan has a non-empty text_hash

  Policy integrity
    * every Policy has a non-empty version

  Model provenance
    * every ModelRun has a non-empty prompt_version

  Human review
    * every ReviewDecision has a valid decision enum value
    * every RiskFinding has at most one current (non-superseded) ReviewDecision
    * no orphan decision chains

Usage:
    python -m src.evaluate
"""

from __future__ import annotations

import sys
from typing import Any

from . import db


def evaluate_findings(session: Any) -> tuple[list[str], list[str]]:
    rows = db.read_reportable_findings(session)
    passes: list[str] = []
    failures: list[str] = []

    for r in rows:
        fid = r["finding_id"]
        issues: list[str] = []
        if r["claim_count"] < 1:
            issues.append("no Claim")
        if r["span_count"] < 1:
            issues.append("no SourceSpan")
        if r["policy_count"] < 1:
            issues.append("no Policy")
        if r["model_run_count"] < 1:
            issues.append("no ModelRun")
        if issues:
            failures.append(f"{fid} ({r['severity']}): missing provenance: {', '.join(issues)}")
        else:
            passes.append(f"{fid} ({r['severity']}): {r['claim_count']} claim(s), full provenance")
    return passes, failures


def evaluate_decision_chains(session: Any) -> list[str]:
    """Detect orphan decisions: multiple decisions on the same finding that
    are not linked by SUPERSEDES.
    """
    result = session.run(
        """
        MATCH (f:RiskFinding)<-[:REVIEWS]-(d:ReviewDecision)
        WITH f, collect(d) AS decisions
        WHERE size(decisions) > 1
        UNWIND decisions AS d
        WITH f, d, decisions
        WHERE NOT EXISTS { MATCH (d)-[:SUPERSEDES]->(:ReviewDecision) }
          AND NOT EXISTS { MATCH (:ReviewDecision)-[:SUPERSEDES]->(d) }
        RETURN f.finding_id AS finding_id, d.decision_id AS orphan_decision_id
        """
    )
    return [f"finding {r['finding_id']}: orphan decision {r['orphan_decision_id']}" for r in result]


def _header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Integrity Evaluation")
    print("=" * 70)

    try:
        with db.session_scope() as session:
            finding_passes, finding_failures = evaluate_findings(session)
            claim_violations = db.read_claims_with_violations(session)
            empty_hash_spans = db.read_spans_with_empty_hash(session)
            unversioned_policies = db.read_policies_missing_version(session)
            unprompted_runs = db.read_model_runs_missing_prompt(session)
            bad_decisions = db.read_invalid_review_decisions(session)
            multi_current = db.read_findings_with_multiple_current_decisions(session)
            missing_status = db.read_findings_missing_status(session)
            decision_orphans = evaluate_decision_chains(session)

            counts = {
                "findings": db.count_nodes(session, "RiskFinding"),
                "claims": db.count_nodes(session, "Claim"),
                "source_spans": db.count_nodes(session, "SourceSpan"),
                "policies": db.count_nodes(session, "Policy"),
                "model_runs": db.count_nodes(session, "ModelRun"),
                "review_decisions": db.count_nodes(session, "ReviewDecision"),
            }
    except Exception as exc:  # noqa: BLE001
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    _header("Integrity Evaluation")
    print(f"Findings checked:         {counts['findings']}")
    print(f"Claims checked:           {counts['claims']}")
    print(f"Source spans checked:     {counts['source_spans']}")
    print(f"Policies checked:         {counts['policies']}")
    print(f"Model runs checked:       {counts['model_runs']}")
    print(f"Review decisions checked: {counts['review_decisions']}")
    print()

    failures: list[str] = []
    failures += finding_failures
    failures += [f"claim {v['claim_id']}: invalid status/confidence ({v['status']}, {v['confidence']})" for v in claim_violations]
    failures += [f"span {s}: empty text_hash" for s in empty_hash_spans]
    failures += [f"policy {p}: missing version" for p in unversioned_policies]
    failures += [f"model run {m}: missing prompt_version" for m in unprompted_runs]
    failures += [f"decision {d['decision_id']}: invalid decision enum ({d['decision']})" for d in bad_decisions]
    failures += [f"finding {m['finding_id']}: multiple current review decisions ({m['current_count']})" for m in multi_current]
    failures += [f"finding {s}: missing proposed_status" for s in missing_status]
    failures += decision_orphans

    if finding_failures:
        print("FAIL: some reportable findings have incomplete provenance")
        for f in finding_failures:
            print(f"  - {f}")
    else:
        print("PASS: all reportable findings have complete provenance")

    if any(v for v in claim_violations) or empty_hash_spans:
        print("FAIL: some claims/spans violate integrity rules")
    else:
        print("PASS: all claims are source-span grounded with valid status/confidence")

    if unprompted_runs:
        print("FAIL: model runs missing prompt_version")
    else:
        print("PASS: all model runs are recorded with prompt provenance")

    if bad_decisions or multi_current or decision_orphans:
        print("FAIL: review decision integrity violations")
    else:
        print("PASS: no destructive review overwrite detected")

    if unversioned_policies:
        print("FAIL: some policies missing version")
    else:
        print("PASS: all policies versioned")

    print()
    print("OVERALL: " + ("PASS" if not failures else f"FAIL ({len(failures)} issue(s))"))
    if failures:
        print()
        print("Issues:")
        for f in failures:
            print(f"  - {f}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
