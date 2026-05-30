"""Simulated AI extraction.

This module does NOT call any external LLM API. It loads the deterministic
"expected findings" from sample-data/expected_findings.json and writes the
corresponding Claim and RiskFinding nodes (with their provenance edges) into
the graph.

Usage:
    python -m src.review
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import db
from .config import SAMPLE_DATA_DIR


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def build_claim(finding: dict, created_at: str) -> dict:
    return {
        "claim_id": finding["claim_id"],
        "claim_text": finding["claim_text"],
        "claim_type": finding.get("claim_type", "policy_tension"),
        "confidence": finding.get("confidence", 0.82),
        "status": "proposed",
        "created_at": created_at,
        "span_id": finding["span_id"],
        "model_run_id": finding["model_run_id"],
    }


def build_finding(finding: dict, created_at: str) -> dict:
    return {
        "finding_id": finding["finding_id"],
        "finding_type": finding["finding_type"],
        "severity": finding["severity"],
        "finding_summary": finding["explanation"],
        "proposed_status": "proposed",
        "created_at": created_at,
        "reportable": finding["reportable"],
    }


def run_review(session: Any) -> tuple[int, int]:
    expected = load_json(SAMPLE_DATA_DIR / "expected_findings.json")
    model_run = load_json(SAMPLE_DATA_DIR / "model_run.json")
    created_at = model_run["run_timestamp"]

    claim_count = 0
    finding_count = 0

    for f in expected["findings"]:
        claim = build_claim(f, created_at)
        db.upsert_claim(session, claim)
        claim_count += 1

        # Claim -> Clause asserts and amendments
        if f.get("clause_id"):
            db.link_claim_asserts_clause(session, f["claim_id"], f["clause_id"])
        if f.get("amends_clause_id"):
            db.link_claim_amends_clause(session, f["claim_id"], f["amends_clause_id"])

        # Claim -> Policy
        relationship = f.get("relationship_to_policy", "TENSIONS_WITH")
        db.link_claim_to_policy(session, f["claim_id"], f["policy_id"], relationship)

        # Finding
        finding_node = build_finding(f, created_at)
        db.upsert_finding(session, finding_node, claim_ids=[f["claim_id"]])
        finding_count += 1

    return claim_count, finding_count


def main() -> int:
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Review (Stubbed Extraction)")
    print("=" * 70)
    try:
        with db.session_scope() as session:
            claims, findings = run_review(session)
        print(f"Created {claims} claim(s) and {findings} risk finding(s).")
        print("AI proposes; counsel disposes. Use src.curate to record review decisions.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Review failed: {exc}", file=sys.stderr)
        print("Hint: ensure src.ingest has run successfully first.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
