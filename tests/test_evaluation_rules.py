"""Tests for evaluation rules.

These tests do not require a live Neo4j; they exercise the evaluation logic
against in-memory rows of the same shape that `db.read_reportable_findings`
returns.
"""

from __future__ import annotations

from typing import Any

import pytest

from src import evaluate


class _StubResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _StubSession:
    """Minimal session stub for evaluate_findings / evaluate_decision_chains."""

    def __init__(self, findings_rows: list[dict], decision_rows: list[dict] | None = None):
        self._findings_rows = findings_rows
        self._decision_rows = decision_rows or []

    def run(self, query: str, **params: Any) -> _StubResult:
        # The evaluator only runs one query inside evaluate_decision_chains;
        # all reportable-findings reads go through db.read_reportable_findings,
        # which we monkeypatch in tests.
        return _StubResult(self._decision_rows)


def _row(
    finding_id: str,
    claim_count: int = 1,
    span_count: int = 1,
    policy_count: int = 1,
    model_run_count: int = 1,
    severity: str = "high",
    summary: str = "summary",
) -> dict:
    return {
        "finding_id": finding_id,
        "finding_type": "indemnification_narrowed",
        "severity": severity,
        "finding_summary": summary,
        "claim_count": claim_count,
        "span_count": span_count,
        "model_run_count": model_run_count,
        "policy_count": policy_count,
    }


def test_evaluation_passes_for_complete_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [_row("FINDING-001"), _row("FINDING-002"), _row("FINDING-003")]
    monkeypatch.setattr(evaluate.db, "read_reportable_findings", lambda s: rows)
    session = _StubSession(rows)
    passes, failures = evaluate.evaluate_findings(session)
    assert len(passes) == 3
    assert failures == []


def test_evaluation_fails_when_provenance_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _row("FINDING-001"),
        _row("FINDING-002", span_count=0),  # missing span
        _row("FINDING-003", model_run_count=0),  # missing model run
        _row("FINDING-004", claim_count=0, span_count=0, model_run_count=0, policy_count=0),
    ]
    monkeypatch.setattr(evaluate.db, "read_reportable_findings", lambda s: rows)
    session = _StubSession(rows)
    passes, failures = evaluate.evaluate_findings(session)
    assert len(passes) == 1
    assert len(failures) == 3
    assert any("FINDING-002" in f and "SourceSpan" in f for f in failures)
    assert any("FINDING-003" in f and "ModelRun" in f for f in failures)


def test_evaluation_detects_no_decision_chain_issues_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _StubSession([], decision_rows=[])
    issues = evaluate.evaluate_decision_chains(session)
    assert issues == []


def test_evaluation_detects_orphan_decisions() -> None:
    decision_rows = [
        {"finding_id": "FINDING-001", "orphan_decision_id": "DEC-orphan-1"},
        {"finding_id": "FINDING-001", "orphan_decision_id": "DEC-orphan-2"},
    ]
    session = _StubSession([], decision_rows=decision_rows)
    issues = evaluate.evaluate_decision_chains(session)
    assert len(issues) == 2
    assert all("FINDING-001" in i for i in issues)
