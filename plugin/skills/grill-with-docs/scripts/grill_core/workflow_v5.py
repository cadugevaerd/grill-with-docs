"""Managed v5 workflow; historical validators and assets remain immutable."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
try:
    from . import workflow_v4 as legacy
except ImportError:
    from grill_core import workflow_v4 as legacy

ASSETS = Path(__file__).resolve().parents[2] / "assets"
VERSION = "v5"
MARKER = "grill-with-docs-workflow:v5"
REGISTRY = ASSETS / "workflow-step-skills.v5.json"
REGISTRY_REF = "assets/workflow-step-skills.v5.json"
TEMPLATE_V5 = ASSETS / "WORKFLOW.v5.template.md"
Failure = legacy.Failure
Gate = legacy.Gate
load_workflow = legacy.load_workflow
marker_version = legacy.marker_version
REGISTRY_SHA256_PLACEHOLDER = legacy.REGISTRY_SHA256_PLACEHOLDER
pinned_registry_sha256 = legacy.pinned_registry_sha256

ESSENTIAL = (
    "## Loop externo",
    "## Ciclo externo de execução",
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "partition",
    "implement-parallel",
    "converge",
    "verify",
    "review",
    "ship",
    "PLAN_ONLY_STOP",
    "Spec Kit >=0.11.2",
    "A–E",
    "no PR",
    "hotfix-fast",
    "HOTFIX-GO",
    "## Invocação canônica",
    "invoke, do not emulate",
    "invocar a skill registrada",
    "semantic emulation",
    "workflow-step-skills/v1",
    "workflow-step-skills.v5.json",
    "registry_sha256",
    "CANONICAL_SKILL",
    "skill-resolution",
    "skill-invocation",
    "step-output",
    "UNATTESTED_STEP_OUTPUT",
    "BLOCKED_CAPABILITY",
    "POLICY_VIOLATION/DIRECT_STEP_EXECUTION",
    "## Execução paralela",
    "Execution DAG",
    "PARTITION-DEGRADED",
    "Evidence Boundary",
    "workflow-tier-models.json",
    "## Eficiência e revisão v5",
    "agent-orchestration.v2.json",
)

def render_v5(template_text: str | None = None) -> bytes:
    text = TEMPLATE_V5.read_text(encoding="utf-8") if template_text is None else template_text
    if text.count(REGISTRY_SHA256_PLACEHOLDER) != 1:
        raise Failure("TEMPLATE_INVALID", "v5 template requires one registry placeholder")
    digest = "sha256:" + hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    return text.replace(REGISTRY_SHA256_PLACEHOLDER, digest).encode("utf-8")


def compatible_v5(text: str) -> bool:
    # v5 preserves the eleven-step grammar; v4's frozen parser owns that grammar.
    return all(item in text for item in ESSENTIAL) and legacy.canonical_step_order(text)


def execution_gate(text: str) -> Gate:
    markers = re.findall(r"grill-with-docs-workflow:(v\d+)", text)
    if markers not in ([], [VERSION]) or not compatible_v5(text):
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", ())
    try:
        current = "sha256:" + hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    except OSError:
        return Gate("BLOCKED", "REGISTRY_PIN_DIVERGENT", ())
    if pinned_registry_sha256(text) != current:
        return Gate("BLOCKED", "REGISTRY_PIN_DIVERGENT", ())
    return Gate("OK", None, ())
