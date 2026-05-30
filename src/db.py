"""Neo4j helper functions.

All Cypher is parameterized. No string concatenation of user-supplied values into
queries. clear_demo_data() is for the local reference model only and should
never be called against a real corpus.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from .config import neo4j_config

try:
    from neo4j import GraphDatabase, Driver, Session
except ImportError:  # pragma: no cover - allow import without neo4j installed
    GraphDatabase = None  # type: ignore[assignment]
    Driver = Any  # type: ignore[assignment,misc]
    Session = Any  # type: ignore[assignment,misc]


def get_driver():
    if GraphDatabase is None:
        raise RuntimeError(
            "neo4j driver is not installed. Run `pip install -e .` first."
        )
    cfg = neo4j_config()
    return GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))


@contextmanager
def session_scope() -> Iterator[Any]:
    driver = get_driver()
    cfg = neo4j_config()
    try:
        with driver.session(database=cfg.database) as session:
            yield session
    finally:
        driver.close()


def create_constraints(session: Any) -> None:
    """Create uniqueness constraints for the demo graph."""
    constraints = [
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
        "CREATE CONSTRAINT span_id IF NOT EXISTS FOR (n:SourceSpan) REQUIRE n.span_id IS UNIQUE",
        "CREATE CONSTRAINT clause_id IF NOT EXISTS FOR (n:Clause) REQUIRE n.clause_id IS UNIQUE",
        "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (n:Policy) REQUIRE n.policy_id IS UNIQUE",
        "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (n:Claim) REQUIRE n.claim_id IS UNIQUE",
        "CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (n:RiskFinding) REQUIRE n.finding_id IS UNIQUE",
        "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (n:ReviewDecision) REQUIRE n.decision_id IS UNIQUE",
        "CREATE CONSTRAINT expert_id IF NOT EXISTS FOR (n:Expert) REQUIRE n.expert_id IS UNIQUE",
        "CREATE CONSTRAINT model_run_id IF NOT EXISTS FOR (n:ModelRun) REQUIRE n.model_run_id IS UNIQUE",
    ]
    for stmt in constraints:
        session.run(stmt)


def clear_demo_data(session: Any) -> None:
    """LOCAL DEMO ONLY: deletes all nodes and relationships in the database.

    WARNING: This is destructive. Never call this against a real corpus, a
    shared environment, or any database holding non-demo data. It exists solely
    so that the reference model's `ingest` step can be re-run idempotently in
    a local sandbox.
    """
    session.run("MATCH (n) DETACH DELETE n")


def upsert_document(session: Any, doc: dict) -> None:
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.title = $title,
            d.document_type = $document_type,
            d.version = $version,
            d.effective_date = $effective_date,
            d.source_system = $source_system,
            d.created_at = $created_at
        """,
        **doc,
    )


def upsert_span(session: Any, span: dict) -> None:
    session.run(
        """
        MERGE (s:SourceSpan {span_id: $span_id})
        SET s.document_id = $document_id,
            s.section_label = $section_label,
            s.char_start = $char_start,
            s.char_end = $char_end,
            s.text = $text,
            s.text_hash = $text_hash
        WITH s
        MATCH (d:Document {document_id: $document_id})
        MERGE (d)-[:CONTAINS]->(s)
        """,
        **span,
    )


def upsert_clause(session: Any, clause: dict) -> None:
    span_ids = clause.get("span_ids", [])
    session.run(
        """
        MERGE (c:Clause {clause_id: $clause_id})
        SET c.clause_type = $clause_type,
            c.normalized_title = $normalized_title,
            c.jurisdiction = $jurisdiction,
            c.source_status = $source_status
        """,
        clause_id=clause["clause_id"],
        clause_type=clause["clause_type"],
        normalized_title=clause["normalized_title"],
        jurisdiction=clause["jurisdiction"],
        source_status=clause["source_status"],
    )
    for sid in span_ids:
        session.run(
            """
            MATCH (c:Clause {clause_id: $clause_id})
            MATCH (s:SourceSpan {span_id: $span_id})
            MERGE (c)-[:HAS_SPAN]->(s)
            """,
            clause_id=clause["clause_id"],
            span_id=sid,
        )


def upsert_policy(session: Any, policy: dict) -> None:
    session.run(
        """
        MERGE (p:Policy {policy_id: $policy_id})
        SET p.policy_name = $policy_name,
            p.policy_type = $policy_type,
            p.version = $version,
            p.rule_text = $rule_text,
            p.risk_tolerance = $risk_tolerance,
            p.owner = $owner,
            p.effective_date = $effective_date
        """,
        policy_id=policy["policy_id"],
        policy_name=policy["policy_name"],
        policy_type=policy["policy_type"],
        version=policy["version"],
        rule_text=policy["rule_text"],
        risk_tolerance=policy["risk_tolerance"],
        owner=policy["owner"],
        effective_date=policy["effective_date"],
    )
    prior = policy.get("supersedes_policy_id")
    if prior:
        session.run(
            """
            MATCH (newer:Policy {policy_id: $newer})
            MATCH (older:Policy {policy_id: $older})
            MERGE (newer)-[:SUPERSEDES]->(older)
            """,
            newer=policy["policy_id"],
            older=prior,
        )


def upsert_expert(session: Any, expert: dict) -> None:
    session.run(
        """
        MERGE (e:Expert {expert_id: $expert_id})
        SET e.name = $name,
            e.role = $role,
            e.bar_jurisdiction = $bar_jurisdiction,
            e.organization = $organization
        """,
        **expert,
    )


def upsert_model_run(session: Any, run: dict) -> None:
    session.run(
        """
        MERGE (m:ModelRun {model_run_id: $model_run_id})
        SET m.model_name = $model_name,
            m.model_version = $model_version,
            m.prompt_version = $prompt_version,
            m.run_timestamp = $run_timestamp,
            m.extraction_mode = $extraction_mode
        """,
        model_run_id=run["model_run_id"],
        model_name=run["model_name"],
        model_version=run["model_version"],
        prompt_version=run["prompt_version"],
        run_timestamp=run["run_timestamp"],
        extraction_mode=run["extraction_mode"],
    )


def upsert_claim(session: Any, claim: dict) -> None:
    session.run(
        """
        MERGE (c:Claim {claim_id: $claim_id})
        SET c.claim_text = $claim_text,
            c.claim_type = $claim_type,
            c.confidence = $confidence,
            c.status = $status,
            c.created_at = $created_at
        WITH c
        MATCH (s:SourceSpan {span_id: $span_id})
        MERGE (c)-[:GROUNDED_IN]->(s)
        WITH c
        MATCH (m:ModelRun {model_run_id: $model_run_id})
        MERGE (c)-[:EXTRACTED_BY]->(m)
        """,
        **claim,
    )


def link_claim_to_policy(
    session: Any, claim_id: str, policy_id: str, relationship: str
) -> None:
    if relationship not in ("TENSIONS_WITH", "COMPLIES_WITH", "CREATES_LIABILITY_UNDER"):
        raise ValueError(f"Unsupported claim->policy relationship: {relationship}")
    # Whitelisted relationship type interpolation; the value is constrained above.
    cypher = f"""
        MATCH (c:Claim {{claim_id: $claim_id}})
        MATCH (p:Policy {{policy_id: $policy_id}})
        MERGE (c)-[:{relationship}]->(p)
        """
    session.run(cypher, claim_id=claim_id, policy_id=policy_id)


def link_claim_asserts_clause(session: Any, claim_id: str, clause_id: str) -> None:
    session.run(
        """
        MATCH (c:Claim {claim_id: $claim_id})
        MATCH (cl:Clause {clause_id: $clause_id})
        MERGE (c)-[:ASSERTS]->(cl)
        """,
        claim_id=claim_id,
        clause_id=clause_id,
    )


def link_claim_amends_clause(session: Any, claim_id: str, clause_id: str) -> None:
    session.run(
        """
        MATCH (c:Claim {claim_id: $claim_id})
        MATCH (cl:Clause {clause_id: $clause_id})
        MERGE (c)-[:AMENDS_CLAUSE]->(cl)
        """,
        claim_id=claim_id,
        clause_id=clause_id,
    )


def upsert_finding(session: Any, finding: dict, claim_ids: list[str]) -> None:
    session.run(
        """
        MERGE (f:RiskFinding {finding_id: $finding_id})
        SET f.finding_type = $finding_type,
            f.severity = $severity,
            f.finding_summary = $finding_summary,
            f.proposed_status = $proposed_status,
            f.created_at = $created_at,
            f.reportable = $reportable
        """,
        **finding,
    )
    for cid in claim_ids:
        session.run(
            """
            MATCH (f:RiskFinding {finding_id: $finding_id})
            MATCH (c:Claim {claim_id: $claim_id})
            MERGE (f)-[:BASED_ON]->(c)
            """,
            finding_id=finding["finding_id"],
            claim_id=cid,
        )


def create_review_decision(
    session: Any,
    decision: dict,
    finding_id: str,
    expert_id: str,
    supersedes_decision_id: Optional[str] = None,
) -> None:
    session.run(
        """
        CREATE (d:ReviewDecision {
            decision_id: $decision_id,
            decision: $decision,
            rationale: $rationale,
            decided_at: $decided_at,
            authority_level: $authority_level
        })
        """,
        **decision,
    )
    session.run(
        """
        MATCH (d:ReviewDecision {decision_id: $decision_id})
        MATCH (f:RiskFinding {finding_id: $finding_id})
        MERGE (d)-[:REVIEWS]->(f)
        """,
        decision_id=decision["decision_id"],
        finding_id=finding_id,
    )
    session.run(
        """
        MATCH (d:ReviewDecision {decision_id: $decision_id})
        MATCH (e:Expert {expert_id: $expert_id})
        MERGE (d)-[:MADE_BY]->(e)
        """,
        decision_id=decision["decision_id"],
        expert_id=expert_id,
    )
    if supersedes_decision_id:
        session.run(
            """
            MATCH (new:ReviewDecision {decision_id: $new_id})
            MATCH (old:ReviewDecision {decision_id: $old_id})
            MERGE (new)-[:SUPERSEDES]->(old)
            """,
            new_id=decision["decision_id"],
            old_id=supersedes_decision_id,
        )


def latest_decision_for_finding(session: Any, finding_id: str) -> Optional[dict]:
    """Return the latest (non-superseded) decision for a finding, if any."""
    result = session.run(
        """
        MATCH (d:ReviewDecision)-[:REVIEWS]->(f:RiskFinding {finding_id: $finding_id})
        WHERE NOT EXISTS { MATCH (newer:ReviewDecision)-[:SUPERSEDES]->(d) }
        RETURN d.decision_id AS decision_id,
               d.decision AS decision,
               d.rationale AS rationale,
               d.decided_at AS decided_at,
               d.authority_level AS authority_level
        ORDER BY d.decided_at DESC
        LIMIT 1
        """,
        finding_id=finding_id,
    )
    record = result.single()
    return dict(record) if record else None


def read_reportable_findings(session: Any) -> list[dict]:
    """Return reportable findings with provenance counts."""
    result = session.run(
        """
        MATCH (f:RiskFinding {reportable: true})
        OPTIONAL MATCH (f)-[:BASED_ON]->(c:Claim)
        OPTIONAL MATCH (c)-[:GROUNDED_IN]->(s:SourceSpan)
        OPTIONAL MATCH (c)-[:EXTRACTED_BY]->(m:ModelRun)
        OPTIONAL MATCH (c)-[:TENSIONS_WITH|COMPLIES_WITH|CREATES_LIABILITY_UNDER]->(p:Policy)
        RETURN f.finding_id AS finding_id,
               f.finding_type AS finding_type,
               f.severity AS severity,
               f.finding_summary AS finding_summary,
               count(DISTINCT c) AS claim_count,
               count(DISTINCT s) AS span_count,
               count(DISTINCT m) AS model_run_count,
               count(DISTINCT p) AS policy_count
        ORDER BY f.severity DESC, f.finding_id ASC
        """
    )
    return [dict(r) for r in result]


def count_nodes(session: Any, label: str) -> int:
    if label not in (
        "Document",
        "SourceSpan",
        "Clause",
        "Policy",
        "Claim",
        "RiskFinding",
        "ReviewDecision",
        "Expert",
        "ModelRun",
    ):
        raise ValueError(f"Unsupported node label: {label}")
    result = session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
    record = result.single()
    return int(record["c"]) if record else 0


def read_claims_with_violations(session: Any) -> list[dict]:
    """Return claims whose status or confidence violate schema constraints."""
    result = session.run(
        """
        MATCH (c:Claim)
        WHERE NOT c.status IN ['proposed', 'superseded', 'withdrawn']
           OR c.confidence < 0.0
           OR c.confidence > 1.0
        RETURN c.claim_id AS claim_id, c.status AS status, c.confidence AS confidence
        """
    )
    return [dict(r) for r in result]


def read_spans_with_empty_hash(session: Any) -> list[str]:
    result = session.run(
        """
        MATCH (s:SourceSpan)
        WHERE s.text_hash IS NULL OR s.text_hash = ''
        RETURN s.span_id AS span_id
        """
    )
    return [r["span_id"] for r in result]


def read_policies_missing_version(session: Any) -> list[str]:
    result = session.run(
        """
        MATCH (p:Policy)
        WHERE p.version IS NULL OR p.version = ''
        RETURN p.policy_id AS policy_id
        """
    )
    return [r["policy_id"] for r in result]


def read_model_runs_missing_prompt(session: Any) -> list[str]:
    result = session.run(
        """
        MATCH (m:ModelRun)
        WHERE m.prompt_version IS NULL OR m.prompt_version = ''
        RETURN m.model_run_id AS model_run_id
        """
    )
    return [r["model_run_id"] for r in result]


def read_invalid_review_decisions(session: Any) -> list[dict]:
    result = session.run(
        """
        MATCH (d:ReviewDecision)
        WHERE NOT d.decision IN ['approved_concession', 'rejected', 'escalated']
        RETURN d.decision_id AS decision_id, d.decision AS decision
        """
    )
    return [dict(r) for r in result]


def read_findings_with_multiple_current_decisions(session: Any) -> list[dict]:
    result = session.run(
        """
        MATCH (f:RiskFinding)<-[:REVIEWS]-(d:ReviewDecision)
        WHERE NOT EXISTS { MATCH (newer:ReviewDecision)-[:SUPERSEDES]->(d) }
        WITH f, count(d) AS current_count
        WHERE current_count > 1
        RETURN f.finding_id AS finding_id, current_count
        """
    )
    return [dict(r) for r in result]


def read_findings_missing_status(session: Any) -> list[str]:
    result = session.run(
        """
        MATCH (f:RiskFinding {reportable: true})
        WHERE f.proposed_status IS NULL OR f.proposed_status = ''
        RETURN f.finding_id AS finding_id
        """
    )
    return [r["finding_id"] for r in result]


def read_model_run_provenance(session: Any, model_run_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (c:Claim)-[:EXTRACTED_BY]->(m:ModelRun {model_run_id: $model_run_id})
        RETURN c.claim_id AS claim_id,
               c.claim_type AS claim_type,
               c.status AS status,
               c.confidence AS confidence
        ORDER BY c.claim_id
        """,
        model_run_id=model_run_id,
    )
    return [dict(r) for r in result]
