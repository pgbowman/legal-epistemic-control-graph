"""Static tests of the sample-data graph invariants.

These do not require a live Neo4j; they exercise the same architectural rules
the runtime evaluator checks, but against the JSON sample files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from src.config import SAMPLE_DATA_DIR, SCHEMA_DIR


SCHEMA_VOCAB_RELATIONSHIPS = {
    "TENSIONS_WITH",
    "COMPLIES_WITH",
    "CREATES_LIABILITY_UNDER",
}
SCHEMA_SEVERITIES = {"critical", "high", "medium", "low"}


def _load(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def baseline() -> dict:
    return _load(SAMPLE_DATA_DIR / "baseline_msa.json")


@pytest.fixture(scope="module")
def vendor() -> dict:
    return _load(SAMPLE_DATA_DIR / "vendor_draft_contract.json")


@pytest.fixture(scope="module")
def policy() -> dict:
    return _load(SAMPLE_DATA_DIR / "company_policy.json")


@pytest.fixture(scope="module")
def model_run() -> dict:
    return _load(SAMPLE_DATA_DIR / "model_run.json")


@pytest.fixture(scope="module")
def expected() -> dict:
    return _load(SAMPLE_DATA_DIR / "expected_findings.json")


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load(SCHEMA_DIR / "graph_schema.json")


def _span_index(baseline: dict, vendor: dict) -> dict[str, dict]:
    return {s["span_id"]: s for s in baseline["spans"] + vendor["spans"]}


def _policy_index(policy: dict) -> dict[str, dict]:
    return {p["policy_id"]: p for p in policy["policies"]}


def test_every_expected_finding_references_existing_span(baseline, vendor, expected) -> None:
    spans = _span_index(baseline, vendor)
    missing = [f["finding_id"] for f in expected["findings"] if f["span_id"] not in spans]
    assert missing == [], f"findings referencing unknown spans: {missing}"


def test_every_expected_finding_references_existing_policy(policy, expected) -> None:
    policies = _policy_index(policy)
    missing = [f["finding_id"] for f in expected["findings"] if f["policy_id"] not in policies]
    assert missing == [], f"findings referencing unknown policies: {missing}"


def test_every_expected_finding_references_the_model_run(model_run, expected) -> None:
    expected_id = model_run["model_run_id"]
    bad = [f["finding_id"] for f in expected["findings"] if f["model_run_id"] != expected_id]
    assert bad == [], f"findings with mismatched model_run_id: {bad}"


def test_every_clause_id_in_findings_resolves(baseline, vendor, expected) -> None:
    clauses = {c["clause_id"] for c in baseline["clauses"] + vendor["clauses"]}
    unresolved = []
    for f in expected["findings"]:
        if f.get("clause_id") and f["clause_id"] not in clauses:
            unresolved.append((f["finding_id"], f["clause_id"]))
        if f.get("amends_clause_id") and f["amends_clause_id"] not in clauses:
            unresolved.append((f["finding_id"], f["amends_clause_id"]))
    assert unresolved == [], f"unresolved clause refs: {unresolved}"


def test_every_vendor_clause_has_at_least_one_span(vendor) -> None:
    span_ids = {s["span_id"] for s in vendor["spans"]}
    for clause in vendor["clauses"]:
        clause_spans = clause.get("span_ids", [])
        assert clause_spans, f"vendor clause {clause['clause_id']} has no spans"
        for sid in clause_spans:
            assert sid in span_ids, f"clause {clause['clause_id']} -> unknown span {sid}"


def test_every_baseline_clause_has_at_least_one_span(baseline) -> None:
    span_ids = {s["span_id"] for s in baseline["spans"]}
    for clause in baseline["clauses"]:
        clause_spans = clause.get("span_ids", [])
        assert clause_spans, f"baseline clause {clause['clause_id']} has no spans"
        for sid in clause_spans:
            assert sid in span_ids


def test_every_source_span_has_nonempty_text_hash(baseline, vendor) -> None:
    for s in baseline["spans"] + vendor["spans"]:
        assert s["text_hash"], f"span {s['span_id']} has empty text_hash"
        # Sanity: the hash format is "<algo>:<digest>" in the sample data.
        assert ":" in s["text_hash"], f"span {s['span_id']} hash is not algo-prefixed"


def test_every_reportable_finding_has_explanation(expected) -> None:
    for f in expected["findings"]:
        if f["reportable"]:
            assert f["explanation"].strip(), f"finding {f['finding_id']} has empty explanation"


def test_every_finding_severity_is_in_vocabulary(expected) -> None:
    for f in expected["findings"]:
        assert f["severity"] in SCHEMA_SEVERITIES, (
            f"finding {f['finding_id']} has out-of-vocab severity {f['severity']!r}"
        )


def test_every_relationship_to_policy_is_in_schema_vocabulary(expected) -> None:
    for f in expected["findings"]:
        rel = f.get("relationship_to_policy", "TENSIONS_WITH")
        assert rel in SCHEMA_VOCAB_RELATIONSHIPS, (
            f"finding {f['finding_id']} uses non-vocab relationship {rel!r}"
        )


def test_source_span_offsets_are_well_formed(baseline, vendor) -> None:
    """Every span has non-empty text and char_start < char_end. The offsets are
    addressing metadata; the architecture does not require them to equal the
    length of the displayed excerpt, only that they are well-formed.
    """
    for s in baseline["spans"] + vendor["spans"]:
        assert s["char_start"] >= 0
        assert s["char_start"] < s["char_end"], (
            f"span {s['span_id']} has non-positive length"
        )
        assert s["text"].strip(), f"span {s['span_id']} has empty text"


def test_policy_supersedes_target_exists(policy) -> None:
    """If a policy declares it supersedes another, the target must be in the file."""
    policies = _policy_index(policy)
    for p in policy["policies"]:
        prior = p.get("supersedes_policy_id")
        if prior:
            assert prior in policies, f"{p['policy_id']} supersedes unknown {prior}"


def test_second_model_run_findings_use_same_span_set(baseline, vendor) -> None:
    expected_v2 = _load(SAMPLE_DATA_DIR / "expected_findings_v2.json")
    span_ids = set(_span_index(baseline, vendor).keys())
    bad = [f["finding_id"] for f in expected_v2["findings"] if f["span_id"] not in span_ids]
    assert bad == [], f"v2 findings reference spans outside the corpus: {bad}"


def test_finding_ids_are_unique(expected) -> None:
    ids = [f["finding_id"] for f in expected["findings"]]
    assert len(ids) == len(set(ids)), f"duplicate finding_ids: {ids}"


def test_claim_ids_are_unique(expected) -> None:
    ids = [f["claim_id"] for f in expected["findings"]]
    assert len(ids) == len(set(ids)), f"duplicate claim_ids: {ids}"
