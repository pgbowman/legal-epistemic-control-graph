"""Render a conservative exception report PDF.

Reads from the local sample-data files so the PDF can be regenerated without
a database. Output: reports/exception_report.pdf

The report is intentionally conservative in style: black on white, narrow
margins, two type weights, no charts. It is a working legal artifact, not a
marketing document.

Usage:
    python -m src.render_report
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF

from .config import REPORTS_DIR, SAMPLE_DATA_DIR


FOOTER_TEXT = (
    "Review artifact only. Not legal advice. "
    "AI-proposed findings require counsel review."
)

POLICY_AREA_LABELS = {
    "indemnification": "Indemnification",
    "limitation_of_liability": "Limitation of Liability",
    "payment_terms": "Payment Terms",
    "data_security": "Data Security",
    "ip_infringement": "IP Infringement",
    "remedies": "Remedies",
    "governance": "Governance",
    "other": "Other",
}


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
        span = spans_by_id.get(f["span_id"], {})
        pol = policies_by_id.get(f["policy_id"], {})
        findings.append(
            {
                "finding_id": f["finding_id"],
                "claim_id": f["claim_id"],
                "claim_text": f["claim_text"],
                "finding_type": f["finding_type"],
                "severity": f["severity"],
                "explanation": f["explanation"],
                "reportable": f["reportable"],
                "review_status": "Pending counsel review",
                "policy_area": POLICY_AREA_LABELS.get(pol.get("policy_type", "other"), "Other"),
                "source_section": span.get("section_label", ""),
                "span": span,
                "policy": pol,
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
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, "HITL GraphRAG Exception Report", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
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


def _rule(pdf: ExceptionReportPDF, y_offset: float = 1.0) -> None:
    pdf.ln(y_offset)
    pdf.set_draw_color(180, 180, 180)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(y_offset + 1)


def render_title_page(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    pdf.ln(35)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Contract Exception Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "AI-Proposed Findings for Counsel Review", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(22)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Contract: {data['vendor_document']['title']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Baseline policy version: {data['policy_document']['version']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Model run: {data['model_run']['model_run_id']}", align="C", new_x="LMARGIN", new_y="NEXT")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pdf.cell(0, 7, f"Generated: {today}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(22)

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
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Review artifact only - not legal advice", align="C", new_x="LMARGIN", new_y="NEXT")


def render_executive_summary(pdf: ExceptionReportPDF, data: dict) -> None:
    pdf.add_page()
    _h1(pdf, "Executive Summary")

    findings = [f for f in data["findings"] if f["reportable"]]
    sev = Counter(f["severity"] for f in findings)
    reviewed = sum(1 for f in findings if f["review_status"].lower().startswith("reviewed"))
    pending = len(findings) - reviewed

    _para(
        pdf,
        f"This report contains {len(findings)} AI-proposed risk finding(s) "
        "requiring counsel review on the vendor draft contract. Each finding is "
        "grounded in a specific source span and tensions with a specific policy.",
    )

    _h3(pdf, "Summary")
    # Compact summary table
    pdf.set_font("Helvetica", "", 10)
    rows = [
        ("Total findings", str(len(findings))),
        ("Critical severity", str(sev.get("critical", 0))),
        ("High severity", str(sev.get("high", 0))),
        ("Medium severity", str(sev.get("medium", 0))),
        ("Low severity", str(sev.get("low", 0))),
        ("Reviewed", str(reviewed)),
        ("Pending counsel review", str(pending)),
    ]
    label_w, value_w = 75, 30
    pdf.set_draw_color(160, 160, 160)
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 7, label, border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(value_w, 7, value, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(3)

    _h3(pdf, "Reviewer instructions")
    _para(
        pdf,
        "Each finding below is grounded in a specific source span and a specific "
        "policy. AI-proposed claims and findings have no authority until a reviewer "
        "records a decision. Use the counsel review box on each detail page to "
        "record your decision. Decisions are non-destructive: a later decision "
        "creates a new record and supersedes the prior one without deleting it.",
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
    pdf.ln(2)

    _h2(pdf, "Baseline Template")
    b = data["baseline_document"]
    _kv(pdf, "Document ID", b["document_id"])
    _kv(pdf, "Title", b["title"])
    _kv(pdf, "Version", b["version"])
    _kv(pdf, "Effective date", b["effective_date"])
    pdf.ln(2)

    _h2(pdf, "Company Policy")
    p = data["policy_document"]
    _kv(pdf, "Document ID", p["document_id"])
    _kv(pdf, "Title", p["title"])
    _kv(pdf, "Version", p["version"])
    _kv(pdf, "Effective date", p["effective_date"])
    pdf.ln(2)

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
    pdf.set_draw_color(150, 150, 150)
    # widths sum to 174 (page width 210 minus 18+18 margins)
    widths = [24, 22, 36, 50, 42]
    headers = ["Finding ID", "Severity", "Policy Area", "Source Section", "Review Status"]
    pdf.set_fill_color(235, 235, 235)
    for w, h in zip(widths, headers):
        pdf.cell(w, 7, h, border=1, align="L", fill=True)
    pdf.ln(7)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font("Helvetica", "", 9)
    for f in data["findings"]:
        if not f["reportable"]:
            continue
        cells = [
            f["finding_id"],
            f["severity"].upper(),
            f["policy_area"],
            f["source_section"],
            f["review_status"],
        ]
        # Equal-height single-line row to keep table tidy
        for w, c in zip(widths, cells):
            pdf.cell(w, 6, c[: max(1, int(w / 1.6))], border=1, align="L")
        pdf.ln(6)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(
        0,
        5,
        "Each finding has a detail page below with the source excerpt, the "
        "AI-proposed claim, the policy tension, the provenance trail, and a "
        "counsel review box.",
    )
    pdf.set_text_color(0, 0, 0)


def _counsel_review_box(pdf: ExceptionReportPDF) -> None:
    pdf.ln(2)
    box_left = pdf.l_margin
    box_right = pdf.w - pdf.r_margin
    box_width = box_right - box_left
    start_y = pdf.get_y()

    # Compute the height we need
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Counsel Review", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "[  ]  Approved Concession", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "[  ]  Rejected", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "[  ]  Escalated", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.cell(0, 6, "Rationale:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "_________________________________________________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "_________________________________________________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(28, 6, "Reviewer:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(85, 6, "_____________________________")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(15, 6, "Date:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "_____________________", new_x="LMARGIN", new_y="NEXT")
    end_y = pdf.get_y()

    # Draw the box around the area we just wrote
    pdf.set_draw_color(80, 80, 80)
    pdf.rect(box_left - 1, start_y - 1, box_width + 2, end_y - start_y + 2)
    pdf.set_draw_color(0, 0, 0)


def render_finding_detail(pdf: ExceptionReportPDF, finding: dict) -> None:
    pdf.add_page()
    _h1(pdf, f"Finding {finding['finding_id']}")
    _kv(pdf, "Type", finding["finding_type"])
    _kv(pdf, "Severity", finding["severity"])
    _kv(pdf, "Policy area", finding["policy_area"])
    _kv(pdf, "Reportable", "Yes" if finding["reportable"] else "No")
    _rule(pdf)

    _h2(pdf, "1. Source Evidence")
    span = finding["span"]
    if span:
        _kv(pdf, "Span ID", span.get("span_id", ""))
        _kv(pdf, "Section", span.get("section_label", ""))
        _kv(pdf, "Offsets", f"{span.get('char_start','')}-{span.get('char_end','')}")
        _kv(pdf, "Text hash", span.get("text_hash", ""))
        pdf.ln(1)
        _h3(pdf, "Excerpt")
        _para(pdf, span.get("text", ""))
    _rule(pdf)

    _h2(pdf, "2. AI-Proposed Claim")
    _kv(pdf, "Claim ID", finding["claim_id"])
    _para(pdf, finding["claim_text"])
    _rule(pdf)

    _h2(pdf, "3. Policy Tension")
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
    _rule(pdf)

    _h2(pdf, "4. Provenance Trail")
    clause = finding.get("clause") or {}
    if clause:
        _kv(pdf, "Vendor clause", f"{clause.get('clause_id','')} ({clause.get('source_status','')})")
    _kv(pdf, "Span -> Claim", "GROUNDED_IN")
    _kv(pdf, "Claim -> ModelRun", "EXTRACTED_BY")
    _kv(pdf, "Claim -> Policy", "TENSIONS_WITH")
    _kv(pdf, "Finding -> Claim", "BASED_ON")
    _rule(pdf)

    _h2(pdf, "5. Counsel Review")
    _counsel_review_box(pdf)


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
