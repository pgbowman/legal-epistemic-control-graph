"""Validate sample data against the JSON schema.

Usage:
    python -m src.validate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from .config import SAMPLE_DATA_DIR, SCHEMA_DIR


def load_schema() -> dict:
    with (SCHEMA_DIR / "graph_schema.json").open() as f:
        return json.load(f)


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def _validate(data: Any, definition: dict, name: str) -> list[str]:
    validator = Draft7Validator(definition)
    return [
        f"{name}: {'.'.join(str(p) for p in err.absolute_path)}: {err.message}"
        for err in validator.iter_errors(data)
    ]


def validate_baseline_msa(schema: dict) -> list[str]:
    data = load_json(SAMPLE_DATA_DIR / "baseline_msa.json")
    errors: list[str] = []
    errors += _validate(data["document"], schema["definitions"]["Document"], "baseline.document")
    for span in data["spans"]:
        errors += _validate(span, schema["definitions"]["SourceSpan"], f"baseline.span[{span['span_id']}]")
    for clause in data["clauses"]:
        errors += _validate(clause, schema["definitions"]["Clause"], f"baseline.clause[{clause['clause_id']}]")
    return errors


def validate_company_policy(schema: dict) -> list[str]:
    data = load_json(SAMPLE_DATA_DIR / "company_policy.json")
    errors: list[str] = []
    errors += _validate(data["document"], schema["definitions"]["Document"], "policy.document")
    for policy in data["policies"]:
        errors += _validate(policy, schema["definitions"]["Policy"], f"policy[{policy['policy_id']}]")
    return errors


def validate_vendor_draft(schema: dict) -> list[str]:
    data = load_json(SAMPLE_DATA_DIR / "vendor_draft_contract.json")
    errors: list[str] = []
    errors += _validate(data["document"], schema["definitions"]["Document"], "vendor.document")
    for span in data["spans"]:
        errors += _validate(span, schema["definitions"]["SourceSpan"], f"vendor.span[{span['span_id']}]")
    for clause in data["clauses"]:
        errors += _validate(clause, schema["definitions"]["Clause"], f"vendor.clause[{clause['clause_id']}]")
    for expert in data.get("experts", []):
        errors += _validate(expert, schema["definitions"]["Expert"], f"vendor.expert[{expert['expert_id']}]")
    return errors


def validate_model_run(schema: dict) -> list[str]:
    data = load_json(SAMPLE_DATA_DIR / "model_run.json")
    return _validate(data, schema["definitions"]["ModelRun"], "model_run")


def validate_expected_findings(schema: dict) -> list[str]:
    data = load_json(SAMPLE_DATA_DIR / "expected_findings.json")
    errors: list[str] = []
    for finding in data["findings"]:
        errors += _validate(finding, schema["definitions"]["ExpectedFinding"], f"expected[{finding['finding_id']}]")
    return errors


def run_validation() -> tuple[int, list[str]]:
    schema = load_schema()
    all_errors: list[str] = []
    all_errors += validate_baseline_msa(schema)
    all_errors += validate_company_policy(schema)
    all_errors += validate_vendor_draft(schema)
    all_errors += validate_model_run(schema)
    all_errors += validate_expected_findings(schema)
    return len(all_errors), all_errors


def main() -> int:
    count, errors = run_validation()
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Schema Validation")
    print("=" * 70)
    if count == 0:
        print("PASS: all sample data validates against schema/graph_schema.json")
        return 0
    print(f"FAIL: {count} validation error(s)")
    for e in errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
