"""Record a human reviewer's decision on a risk finding.

Decisions are non-destructive: prior decisions are preserved, and the new
decision is linked via :SUPERSEDES if a prior decision exists for the same
finding.

Usage:
    python -m src.curate --finding-id FINDING-001 \\
        --decision escalated --expert-id EXPERT-001 \\
        --rationale "Requires negotiation with vendor."
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone

from . import db


ALLOWED_DECISIONS = {"approved_concession", "rejected", "escalated"}
ALLOWED_AUTHORITY_LEVELS = {
    "associate",
    "senior_counsel",
    "general_counsel",
    "compliance_officer",
    "external",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a human review decision.")
    parser.add_argument("--finding-id", required=True, help="RiskFinding ID being reviewed")
    parser.add_argument("--decision", required=True, choices=sorted(ALLOWED_DECISIONS))
    parser.add_argument("--expert-id", required=True, help="Expert (reviewer) ID")
    parser.add_argument("--rationale", required=True, help="Human-authored rationale")
    parser.add_argument(
        "--authority-level",
        default="senior_counsel",
        choices=sorted(ALLOWED_AUTHORITY_LEVELS),
        help="Reviewer's authority level",
    )
    parser.add_argument(
        "--decision-id",
        default=None,
        help="Optional explicit decision ID; otherwise a UUID is generated",
    )
    return parser.parse_args(argv)


def build_decision(args: argparse.Namespace) -> dict:
    return {
        "decision_id": args.decision_id or f"DEC-{uuid.uuid4().hex[:12]}",
        "decision": args.decision,
        "rationale": args.rationale,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "authority_level": args.authority_level,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    decision = build_decision(args)

    try:
        with db.session_scope() as session:
            prior = db.latest_decision_for_finding(session, args.finding_id)
            supersedes = prior["decision_id"] if prior else None
            db.create_review_decision(
                session,
                decision=decision,
                finding_id=args.finding_id,
                expert_id=args.expert_id,
                supersedes_decision_id=supersedes,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"Curate failed: {exc}", file=sys.stderr)
        return 1

    print(decision["decision_id"])
    if supersedes:
        print(f"(supersedes prior decision {supersedes})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
