"""Render a conservative exception report PDF.

Reads from the local Neo4j graph if available, otherwise falls back to the
sample-data files so the PDF can be regenerated without a database.

Output: reports/exception_report.pdf

Usage:
    python -m src.render_report
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF

from .config import REPORTS_DIR, SAMPLE_DATA_DIR


FOOTER_TEXT = (
    "Review artifact only. Not legal advice. "
    "AI-proposed findings require counsel review."
)


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def gather_data_from_files() -> dict:
    baseline = load_json(SAMPLE_DATA_DIR / "baseline_msa.json")
    policy = load_json(SAMPLE_DATA_DIR / "company_policy.json")
    vendor = load_json(SAMPLE_DATA_DIR / "vendor_draft_contract.json")
    model_run = load_json(SAMPLE_DATA_DIR / "model_run.json")
    expected = load_json(SAMPLE_DATA_DIR / "expected_findings.json")

    spans_by_id = {s["span_id"]: s for s in baseline["spans"] + vendor["spans"]}
    policies_by_id = {p["policy_id"]: p for p in policy["policies"]}
    clauses_by_id = {
        c["clause_id"]: c for c in baseline["clauses"] + vendor["clauses"]
    }

    findings = []
    for f in expected["findings"]:
        findings.append(
            {
                "finding_id": f["finding_id"],
                "claim_id": f["claim_id"],
                "claim_text": f["claim_text"],
                "finding_type": f["finding_type"],
                "severity": f["severity"],
                "explanation": f["explanation"],
                "reportable": f["reportable"],
                "span": spans_by_id.get(f["span_id"], {}),
                "policy": policies_by_id.get(f["policy_id"], {}),
                "clause": clauses_by_id.get(f.get("clause_id") or "", {}),
            }
        )

    return {
        "baseline_document": baseline["document"],
        "vendor_document": vendor["document"],
        "policy_document": policy["document"],
        "model_run": model_run,
        "findings": findings,
    }


class ExceptionReportPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "HITL GraphRAG Exception Report", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, FOOTER_TEXT, align="C")
        self.set_text_color(0, 0, 0)


def _h1(pdf: ExceptionReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _h2(pdf: ExceptionReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _h3(pdf: ExceptionReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")


def _para(pdf: ExceptionReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, text)
    pdf.ln(1)


def _kv(pdf: ExceptionReportPDF, key: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 6, f"{key}:")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def render_title_page(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Contract Exception Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "AI-Proposed Findings for Counsel Review", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Contract: {data['vendor_document']['title']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Baseline: {data['baseline_document']['title']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Policy version: {data['policy_document']['version']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(
        0,
        6,
        "AI proposes; counsel disposes. This document presents AI-proposed risk "
        "findings that require human legal review. Findings are not legal advice "
        "and do not constitute a decision.",
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(15)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {today}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6, f"Model run: {data['model_run']['model_run_id']}", align="C",
        new_x="LMARGIN", new_y="NEXT"
    )


def render_executive_summary(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    _h1(pdf, "Executive Summary")
    findings = [f for f in data["findings"] if f["reportable"]]
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
    summary = (
        f"This report contains {len(findings)} AI-proposed risk finding(s) "
        f"requiring counsel review on the vendor draft contract."
    )
    _para(pdf, summary)
    _h3(pdf, "Severity breakdown")
    for sev in ("critical", "high", "medium", "low"):
        count = sev_counts.get(sev, 0)
        if count:
            _para(pdf, f"  {sev.capitalize()}: {count}")
    pdf.ln(2)
    _h3(pdf, "Reviewer instructions")
    _para(
        pdf,
        "Each finding below is grounded in a specific source span and a specific "
        "policy. AI-proposed claims and findings have no authority until a "
        "reviewer records a decision. Use the checklist on each finding page "
        "to record your decision. Decisions are non-destructive: a later "
        "decision creates a new record and supersedes the prior one without "
        "deleting it.",
    )


def render_metadata(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    _h1(pdf, "Contract and Policy Metadata")
    _h2(pdf, "Vendor Draft Contract")
    v = data["vendor_document"]
    _kv(pdf, "Document ID", v["document_id"])
    _kv(pdf, "Title", v["title"])
    _kv(pdf, "Version", v["version"])
    _kv(pdf, "Effective date", v["effective_date"])
    _kv(pdf, "Source system", v["source_system"])
    pdf.ln(3)

    _h2(pdf, "Baseline Template")
    b = data["baseline_document"]
    _kv(pdf, "Document ID", b["document_id"])
    _kv(pdf, "Title", b["title"])
    _kv(pdf, "Version", b["version"])
    _kv(pdf, "Effective date", b["effective_date"])
    pdf.ln(3)

    _h2(pdf, "Company Policy")
    p = data["policy_document"]
    _kv(pdf, "Document ID", p["document_id"])
    _kv(pdf, "Title", p["title"])
    _kv(pdf, "Version", p["version"])
    _kv(pdf, "Effective date", p["effective_date"])
    pdf.ln(3)

    _h2(pdf, "Model Run")
    m = data["model_run"]
    _kv(pdf, "Model run ID", m["model_run_id"])
    _kv(pdf, "Model name", m["model_name"])
    _kv(pdf, "Model version", m["model_version"])
    _kv(pdf, "Prompt version", m["prompt_version"])
    _kv(pdf, "Run timestamp", m["run_timestamp"])
    _kv(pdf, "Extraction mode", m["extraction_mode"])


def render_exception_table(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    _h1(pdf, "Exception Table")
    pdf.set_font("Helvetica", "B", 9)
    widths = [22, 48, 20, 84]
    headers = ["Finding", "Type", "Severity", "Summary"]
    for w, h in zip(widths, headers):
        pdf.cell(w, 7, h, border=1)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for f in data["findings"]:
        if not f["reportable"]:
            continue
        row_h = 6
        # Compute lines for the summary to determine row height
        pdf.cell(widths[0], row_h, f["finding_id"], border=1)
        pdf.cell(widths[1], row_h, f["finding_type"], border=1)
        pdf.cell(widths[2], row_h, f["severity"], border=1)
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.multi_cell(widths[3], row_h, f["explanation"][:200], border=1)
        # Move to next line
        pdf.set_xy(pdf.l_margin, max(pdf.get_y(), y + row_h))


def render_finding_detail(pdf: ExceptionReportPDF, finding: dict) -> None:
    pdf.add_page()
    _h1(pdf, f"Finding {finding['finding_id']}")
    _kv(pdf, "Type", finding["finding_type"])
    _kv(pdf, "Severity", finding["severity"])
    _kv(pdf, "Reportable", "Yes" if finding["reportable"] else "No")
    pdf.ln(2)

    _h2(pdf, "Source Span")
    span = finding["span"]
    if span:
        _kv(pdf, "Span ID", span.get("span_id", ""))
        _kv(pdf, "Section", span.get("section_label", ""))
        _kv(pdf, "Offsets", f"{span.get('char_start','')}-{span.get('char_end','')}")
        _kv(pdf, "Text hash", span.get("text_hash", ""))
        pdf.ln(1)
        _h3(pdf, "Excerpt")
        _para(pdf, span.get("text", ""))
    pdf.ln(2)

    _h2(pdf, "AI-Proposed Claim")
    _kv(pdf, "Claim ID", finding["claim_id"])
    _para(pdf, finding["claim_text"])

    _h2(pdf, "Policy Tension")
    policy = finding["policy"]
    if policy:
        _kv(pdf, "Policy ID", policy.get("policy_id", ""))
        _kv(pdf, "Policy", policy.get("policy_name", ""))
        _kv(pdf, "Version", policy.get("version", ""))
        _kv(pdf, "Owner", policy.get("owner", ""))
        _kv(pdf, "Tolerance", policy.get("risk_tolerance", ""))
        pdf.ln(1)
        _h3(pdf, "Rule")
        _para(pdf, policy.get("rule_text", ""))
    pdf.ln(1)
    _h3(pdf, "Explanation")
    _para(pdf, finding["explanation"])

    _h2(pdf, "Provenance Trail")
    clause = finding.get("clause") or {}
    if clause:
        _kv(pdf, "Vendor clause", f"{clause.get('clause_id','')} ({clause.get('source_status','')})")
    _kv(pdf, "Span -> Claim", "GROUNDED_IN")
    _kv(pdf, "Claim -> ModelRun", "EXTRACTED_BY")
    _kv(pdf, "Claim -> Policy", "TENSIONS_WITH")
    _kv(pdf, "Finding -> Claim", "BASED_ON")

    _h2(pdf, "Human Review")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "[  ]  Approved Concession", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "[  ]  Rejected", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "[  ]  Escalated", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    _kv(pdf, "Rationale", "________________________________________________________________")
    pdf.ln(4)
    _kv(pdf, "Reviewer signature", "________________________________________________________________")
    _kv(pdf, "Date", "________________________________________________________________")


def build_pdf(data: dict, output_path: Path) -> Path:
    pdf = ExceptionReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=18, top=18, right=18)

    render_title_page(pdf, data)
    render_executive_summary(pdf, data)
    render_metadata(pdf, data)
    render_exception_table(pdf, data)
    for f in data["findings"]:
        if f["reportable"]:
            render_finding_detail(pdf, f)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path


def main() -> int:
    print("=" * 70)
    print("HITL GraphRAG Reference Model :: Render Exception Report")
    print("=" * 70)
    data = gather_data_from_files()
    output_path = REPORTS_DIR / "exception_report.pdf"
    try:
        build_pdf(data, output_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Render failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
