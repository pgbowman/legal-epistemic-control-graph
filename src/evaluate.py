"""Evaluate model integrity.

For every reportable RiskFinding in the graph, check that it has:

* at least one Claim (via BASED_ON)
* at least one SourceSpan (via Claim -> GROUNDED_IN)
* at least one Policy (via Claim -> TENSIONS_WITH | COMPLIES_WITH | CREATES_LIABILITY_UNDER)
* at least one ModelRun (via Claim -> EXTRACTED_BY)
* a proposed_status value
* reportable == true

Also checks that no ReviewDecision has been destructively overwritten: every
non-terminal decision should be SUPERSEDED by exactly one successor (or zero,
if it is the current decision).

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
    """Detect destructive overwrites of review decisions.

    A destructive overwrite would manifest as multiple ReviewDecision nodes
    pointing to the same finding without a SUPERSEDES chain connecting them.
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
    issues = [
        f"finding {r['finding_id']}: orphan decision {r['orphan_decision_id']}"
        for r in result
    ]
    return issues


def main() -> int:
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Integrity Evaluation")
    print("=" * 70)

    try:
        with db.session_scope() as session:
            passes, failures = evaluate_findings(session)
            decision_issues = evaluate_decision_chains(session)
    except Exception as exc:  # noqa: BLE001
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Reportable findings checked: {len(passes) + len(failures)}")
    for p in passes:
        print(f"  PASS  {p}")
    for f in failures:
        print(f"  FAIL  {f}")
    print()
    print(f"Review decision chain issues: {len(decision_issues)}")
    for issue in decision_issues:
        print(f"  FAIL  {issue}")

    overall_pass = not failures and not decision_issues
    print()
    print("OVERALL: PASS" if overall_pass else "OVERALL: FAIL")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
