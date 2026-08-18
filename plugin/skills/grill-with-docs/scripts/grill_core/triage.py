#!/usr/bin/env python3
"""``grill-triage/v1``: a sealed routing decision derived from a root-cause report.

Why this module exists at all: the public CLI is deterministic stdlib Python and
cannot classify natural language, so ``init`` can never decide by itself whether
a reported problem is an incident, a defect against an existing spec, or missing
functionality. The classification is a *skill* output (``code-debug`` emits the
root-cause report this module parses); what the core can do -- and is the only
thing it does here -- is check that the report proves what it claims and that the
evidence a given route demands is actually present, then seal that decision so a
later ``init``/``hotfix`` can consume it without trusting the operator's word.

The module is deliberately free of any static import from ``grill_workspace``:
the public CLI imports *this* module, never the other way round (same rule as
``grill_core/work_item_v3.py``). It also never touches the filesystem, git or a
child process -- it receives text that ``grill_workspace`` already read through
its own ``safe_read_regular_fd`` boundary, so the security-critical primitives
stay in one place instead of being duplicated into a second implementation.
``canonical``/``hash_bytes`` *are* duplicated, three lines each, because they are
pure and the alternative is the static cycle this boundary exists to prevent.

Vocabulary (LD-002, revisada): every condition named here is triage-only and so
is minted ``SCREAMING_SNAKE``; ``grill_workspace.translate_v3_code`` rewrites it
to the live ``SCREAMING-KEBAB`` spelling at the CLI boundary. Codes that describe
a condition v2 already diagnoses (``SYMLINK-REJECTED``, ``PATH-ESCAPE``,
``SCOPE-NOT-CLOSED``, ``EVIDENCE-MISSING``) are raised by the caller with their
existing spelling and never restated here.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

EXIT_NO_GO = 1
EXIT_BLOCKED = 2

SCHEMA = "grill-triage/v1"
ROUTES = ("bugfix", "feature", "hotfix", "module")
SEVERITIES = ("critical", "high", "low", "medium")
TRIAGE_ID_RE = re.compile(r"^tri-[A-Za-z0-9][A-Za-z0-9._-]{1,100}$")

# The heading and the three status phrases are code-debug's own mandatory output
# format, not an invention of this module. Matching is case-insensitive and
# substring-based because the skill writes them as sentences ("Causa raiz
# comprovada."), but the phrases themselves are literal: a report that words its
# status differently is refused rather than guessed at.
REPORT_HEADING = "# Relatório de debug"
STATUS_PROVEN = "causa raiz comprovada"
STATUS_UNPROVEN = "causa raiz não comprovada ainda"
STATUS_ENV_BLOCKED = "bloqueado por ambiente"
STATUSES = (STATUS_PROVEN, STATUS_UNPROVEN, STATUS_ENV_BLOCKED)

ROOT_CAUSE_SECTION = "Causa raiz"
REQUIRED_SECTIONS = (
    "Sintoma reproduzido",
    "Evidências",
    ROOT_CAUSE_SECTION,
    "Cadeia causal",
    "Arquivos envolvidos",
)

# The routing gate. Each route names the evidence it cannot open without and the
# evidence that contradicts it. A closed scope plus a rollback is what makes an
# incident containable; a spec reference is what makes a defect a deviation from
# something already agreed instead of missing functionality -- so requiring one
# and forbidding the other is what keeps the two routes from collapsing into a
# matter of taste.
ROUTE_EVIDENCE: dict[str, dict[str, tuple[str, ...]]] = {
    "hotfix": {"requires": ("production_impact", "scope", "rollback"), "forbids": ("spec_ref",)},
    "bugfix": {"requires": ("spec_ref",), "forbids": ("scope", "rollback")},
    "feature": {"requires": (), "forbids": ("spec_ref", "scope", "rollback")},
    "module": {"requires": (), "forbids": ("spec_ref", "scope", "rollback")},
}
HOTFIX_SEVERITY = "critical"


@dataclass
class TriageError(Exception):
    """Structured failure with the same shape as ``grill_workspace.CliFailure``."""

    exit_code: int
    verdict: str
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "code": self.code, "error": self.message, **self.details}


def blocked(code: str, message: str, **details: Any) -> TriageError:
    return TriageError(EXIT_BLOCKED, "BLOCKED", code, message, details)


def no_go(code: str, message: str, **details: Any) -> TriageError:
    return TriageError(EXIT_NO_GO, "NO-GO", code, message, details)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_sections(text: str) -> dict[str, str]:
    """Map every ``## `` heading to its stripped body. A repeated heading keeps the last body."""
    sections: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                sections[title] = "\n".join(body).strip()
            title = line[3:].strip()
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections[title] = "\n".join(body).strip()
    return sections


def parse_report(text: str) -> dict[str, Any]:
    """Validate the document is a code-debug report and extract its status.

    Structure is checked before meaning on purpose: an unproven report is a
    perfectly well-formed report, so refusing it as ``TRIAGE_REPORT_INCOMPLETE``
    would name the wrong defect and send the operator to fix the document rather
    than finish the investigation.
    """
    if REPORT_HEADING not in text:
        raise blocked(
            "TRIAGE_REPORT_INVALID",
            "report is not a code-debug root-cause report",
            expected_heading=REPORT_HEADING,
        )
    sections = split_sections(text)
    missing = [name for name in REQUIRED_SECTIONS if not sections.get(name)]
    if missing:
        raise blocked(
            "TRIAGE_REPORT_INCOMPLETE",
            "report is missing required non-empty sections",
            missing_sections=missing,
        )
    status_body = sections.get("Status")
    if not status_body:
        raise blocked("TRIAGE_REPORT_INVALID", "report has no non-empty '## Status' section")
    status = declared_status(status_body)
    if status is None:
        raise blocked(
            "TRIAGE_REPORT_INVALID",
            "'## Status' does not declare a known code-debug status",
            accepted_statuses=list(STATUSES),
        )
    # A report whose header claims proof while its own root-cause section still
    # says the cause is unproven contradicts itself. The weaker of the two wins:
    # a seal is worth nothing if it can be obtained by editing one line.
    if status == STATUS_PROVEN and STATUS_UNPROVEN in sections[ROOT_CAUSE_SECTION].lower():
        status = STATUS_UNPROVEN
    return {"status": status, "sections": sections}


def declared_status(status_body: str) -> str | None:
    """Return the status phrase the body declares, or ``None``.

    ``STATUS_UNPROVEN`` is tested first: it is the negation of ``STATUS_PROVEN``
    and a naive ordering would read "não comprovada ainda" as proof.
    """
    lowered = status_body.lower()
    for phrase in (STATUS_UNPROVEN, STATUS_ENV_BLOCKED, STATUS_PROVEN):
        if phrase in lowered:
            return phrase
    return None


def require_proven(parsed: dict[str, Any]) -> None:
    if parsed["status"] != STATUS_PROVEN:
        raise no_go(
            "ROOT_CAUSE_UNPROVEN",
            "no route opens until the report proves the root cause",
            report_status=parsed["status"],
        )


def check_route_evidence(
    route: str,
    *,
    severity: str,
    production_impact: bool,
    spec_ref: dict[str, Any] | None,
    scope: list[str],
    rollback: str | None,
) -> None:
    if route not in ROUTES:
        raise blocked("INVALID_ROUTE", route, accepted_routes=list(ROUTES))
    if severity not in SEVERITIES:
        raise blocked("INVALID_SEVERITY", severity, accepted_severities=list(SEVERITIES))
    present = {
        "production_impact": bool(production_impact),
        "spec_ref": spec_ref is not None,
        "scope": bool(scope),
        "rollback": bool(rollback),
    }
    rules = ROUTE_EVIDENCE[route]
    missing = [name for name in rules["requires"] if not present[name]]
    if route == "hotfix" and severity != HOTFIX_SEVERITY:
        missing.append(f"severity={HOTFIX_SEVERITY}")
    if missing:
        raise no_go(
            "ROUTE_EVIDENCE_MISSING",
            f"route {route} requires evidence that was not supplied",
            route=route,
            missing_evidence=sorted(missing),
        )
    conflicting = [name for name in rules["forbids"] if present[name]]
    if conflicting:
        raise no_go(
            "ROUTE_EVIDENCE_CONFLICT",
            f"route {route} forbids evidence that was supplied",
            route=route,
            forbidden_evidence=sorted(conflicting),
        )


def build_record(
    *,
    triage_id: str,
    route: str,
    severity: str,
    production_impact: bool,
    report: dict[str, str],
    spec_ref: dict[str, str] | None,
    scope: list[str],
    rollback: str | None,
    recorded_at_commit: str | None,
) -> dict[str, Any]:
    """Build the unsealed record. Every field is already validated by the caller."""
    if not TRIAGE_ID_RE.fullmatch(triage_id):
        raise blocked("INVALID_TRIAGE_ID", triage_id)
    return {
        "schema": SCHEMA,
        "triage_id": triage_id,
        "route": route,
        "severity": severity,
        "production_impact": bool(production_impact),
        "report": report,
        "spec_ref": spec_ref,
        "scope": {"paths": list(scope)},
        "rollback": rollback,
        "recorded_at_commit": recorded_at_commit,
    }


def seal(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "triage_sha256": hash_bytes(canonical(record))}


def verify_seal(record: Any) -> dict[str, Any]:
    """Return the unsealed body of a record read back from disk.

    The seal covers the whole record minus the seal itself, the same construction
    ``immutable_sha256`` and ``hotfix_sha256`` already use for work items.
    """
    if not isinstance(record, dict) or not isinstance(record.get("triage_sha256"), str):
        raise blocked("TRIAGE_TAMPERED", "record carries no seal")
    body = {key: value for key, value in record.items() if key != "triage_sha256"}
    if hash_bytes(canonical(body)) != record["triage_sha256"]:
        raise blocked("TRIAGE_TAMPERED", "record seal does not match its content")
    return body
