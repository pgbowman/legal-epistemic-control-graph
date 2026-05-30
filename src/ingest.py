"""Ingest baseline MSA, company policy, vendor draft contract, and model run
into Neo4j.

Usage:
    python -m src.ingest
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


def ingest_baseline(session: Any) -> tuple[int, int, int]:
    data = load_json(SAMPLE_DATA_DIR / "baseline_msa.json")
    db.upsert_document(session, data["document"])
    for span in data["spans"]:
        db.upsert_span(session, span)
    for clause in data["clauses"]:
        db.upsert_clause(session, clause)
    return 1, len(data["spans"]), len(data["clauses"])


def ingest_policy(session: Any) -> tuple[int, int]:
    data = load_json(SAMPLE_DATA_DIR / "company_policy.json")
    db.upsert_document(session, data["document"])
    for policy in data["policies"]:
        db.upsert_policy(session, policy)
    return 1, len(data["policies"])


def ingest_vendor(session: Any) -> tuple[int, int, int, int]:
    data = load_json(SAMPLE_DATA_DIR / "vendor_draft_contract.json")
    db.upsert_document(session, data["document"])
    for span in data["spans"]:
        db.upsert_span(session, span)
    for clause in data["clauses"]:
        db.upsert_clause(session, clause)
    experts = data.get("experts", [])
    for expert in experts:
        db.upsert_expert(session, expert)
    return 1, len(data["spans"]), len(data["clauses"]), len(experts)


def ingest_model_run(session: Any) -> int:
    run = load_json(SAMPLE_DATA_DIR / "model_run.json")
    db.upsert_model_run(session, run)
    return 1


def main() -> int:
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Ingest")
    print("=" * 70)

    try:
        with db.session_scope() as session:
            db.create_constraints(session)
            db.clear_demo_data(session)
            # Constraints survive a DETACH DELETE; recreate to be safe in case
            # the DB was wiped externally.
            db.create_constraints(session)

            b_docs, b_spans, b_clauses = ingest_baseline(session)
            p_docs, p_policies = ingest_policy(session)
            v_docs, v_spans, v_clauses, v_experts = ingest_vendor(session)
            m_runs = ingest_model_run(session)

        print(f"baseline_msa: {b_docs} document, {b_spans} spans, {b_clauses} clauses")
        print(f"company_policy: {p_docs} document, {p_policies} policies")
        print(f"vendor_draft: {v_docs} document, {v_spans} spans, {v_clauses} clauses, {v_experts} experts")
        print(f"model_run: {m_runs} run")
        print("Ingest complete.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Ingest failed: {exc}", file=sys.stderr)
        print("Hint: ensure Neo4j is running and .env credentials are correct.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
