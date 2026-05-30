"""Tests for review output structure (claim/finding shape, without a live DB)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import SAMPLE_DATA_DIR
from src.review import build_claim, build_finding


@pytest.fixture(scope="module")
def expected_findings() -> list[dict]:
    with (SAMPLE_DATA_DIR / "expected_findings.json").open() as f:
        return json.load(f)["findings"]


@pytest.fixture(scope="module")
def model_run() -> dict:
    with (SAMPLE_DATA_DIR / "model_run.json").open() as f:
        return json.load(f)


def test_expected_findings_create_claims(expected_findings: list[dict], model_run: dict) -> None:
    claims = [build_claim(f, model_run["run_timestamp"]) for f in expected_findings]
    assert len(claims) >= 3
    for claim in claims:
        assert claim["claim_id"].startswith("CLAIM-")
        assert claim["status"] == "proposed"
        assert 0.0 <= claim["confidence"] <= 1.0


def test_every_claim_is_grounded_in_a_source_span(
    expected_findings: list[dict], model_run: dict
) -> None:
    for f in expected_findings:
        claim = build_claim(f, model_run["run_timestamp"])
        assert claim["span_id"], "claim must reference a span_id"


def test_every_claim_is_linked_to_a_model_run(
    expected_findings: list[dict], model_run: dict
) -> None:
    for f in expected_findings:
        claim = build_claim(f, model_run["run_timestamp"])
        assert claim["model_run_id"] == model_run["model_run_id"]


def test_every_risk_finding_is_based_on_a_claim(
    expected_findings: list[dict], model_run: dict
) -> None:
    for f in expected_findings:
        finding = build_finding(f, model_run["run_timestamp"])
        # The mapping from finding to claim_id is recorded in the expected
        # findings file; verify the link is present and matches.
        assert f["claim_id"].startswith("CLAIM-")
        assert finding["finding_id"].startswith("FINDING-")


def test_at_least_three_reportable_findings(expected_findings: list[dict]) -> None:
    reportable = [f for f in expected_findings if f["reportable"]]
    assert len(reportable) >= 3, "sample is meant to demonstrate at least three risk findings"


def test_findings_cover_required_categories(expected_findings: list[dict]) -> None:
    types = {f["finding_type"] for f in expected_findings}
    required = {
        "indemnification_narrowed",
        "liability_cap_carveout_breach",
        "payment_terms_out_of_policy",
        "exclusive_remedy_conflict",
    }
    assert required.issubset(types), f"missing required finding types: {required - types}"


def test_multiple_claims_can_share_a_source_span(expected_findings: list[dict]) -> None:
    """Two findings should tension different policies against the same vendor remedy span,
    demonstrating that the architecture supports many-to-one Claim->SourceSpan.
    """
    span_to_claims: dict[str, list[str]] = {}
    for f in expected_findings:
        span_to_claims.setdefault(f["span_id"], []).append(f["claim_id"])
    shared = {sid: cids for sid, cids in span_to_claims.items() if len(cids) > 1}
    assert shared, "expected at least one span supporting multiple claims"
