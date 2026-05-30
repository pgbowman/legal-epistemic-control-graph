"""Tests for schema validation of sample data."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from src.validate import (
    load_schema,
    validate_baseline_msa,
    validate_company_policy,
    validate_expected_findings,
    validate_model_run,
    validate_vendor_draft,
)


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_schema()


def test_sample_baseline_validates(schema: dict) -> None:
    assert validate_baseline_msa(schema) == []


def test_sample_policy_validates(schema: dict) -> None:
    assert validate_company_policy(schema) == []


def test_sample_vendor_validates(schema: dict) -> None:
    assert validate_vendor_draft(schema) == []


def test_sample_model_run_validates(schema: dict) -> None:
    assert validate_model_run(schema) == []


def test_sample_expected_findings_validate(schema: dict) -> None:
    assert validate_expected_findings(schema) == []


def test_invalid_curation_status_fails(schema: dict) -> None:
    """A ReviewDecision with an invalid `decision` value must fail validation."""
    decision_schema = schema["definitions"]["ReviewDecision"]
    validator = Draft7Validator(decision_schema)
    bad = {
        "decision_id": "DEC-bad",
        "decision": "needs_more_thought",  # not in enum
        "rationale": "n/a",
        "decided_at": "2026-05-30T12:00:00Z",
        "authority_level": "senior_counsel",
    }
    errors = list(validator.iter_errors(bad))
    assert any("decision" in str(e.path) or "not one of" in e.message for e in errors)


def test_invalid_finding_status_fails(schema: dict) -> None:
    finding_schema = schema["definitions"]["RiskFinding"]
    validator = Draft7Validator(finding_schema)
    bad = {
        "finding_id": "FINDING-bad",
        "finding_type": "indemnification_narrowed",
        "severity": "high",
        "finding_summary": "...",
        "proposed_status": "in_progress",  # not in enum
        "created_at": "2026-05-30T12:00:00Z",
        "reportable": True,
    }
    errors = list(validator.iter_errors(bad))
    assert errors, "expected validation errors for invalid proposed_status"


def test_invalid_claim_status_fails(schema: dict) -> None:
    claim_schema = schema["definitions"]["Claim"]
    validator = Draft7Validator(claim_schema)
    bad = {
        "claim_id": "CLAIM-bad",
        "claim_text": "...",
        "claim_type": "policy_tension",
        "confidence": 0.9,
        "status": "decided",  # not in enum
        "created_at": "2026-05-30T12:00:00Z",
    }
    errors = list(validator.iter_errors(bad))
    assert errors
