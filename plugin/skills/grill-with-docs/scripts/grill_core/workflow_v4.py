#!/usr/bin/env python3
"""Managed WORKFLOW.md v4 (parallel execution) plus preview-first migration to it.

Stdlib only, no network, no runtime CLI dependency.

Coexistence contract
--------------------
v4 is a NEW marker with a NEW allowlist, exactly as v3 was to v2.
``workflow_v3.ESSENTIAL`` and ``ensure_workflow.ESSENTIAL`` are read here and
never modified: appending a v4 substring to either tuple would turn every
WORKFLOW.md already materialised in a consumer repository into "incompatible
workflow" and block ``init``/``preflight`` for people who changed nothing. A v2
or v3 workflow stays byte-intact on read, detection and preview; only an
explicitly authorised mutable command may rewrite it.

The same reasoning governs the assets: v4 ships its own registry, its own
catalogue (with its own ``catalog_id``) and its own trust snapshot rather than
editing v3's. A v3 document pins the v3 ``registry_sha256`` in its own prose, so
repointing that asset in place would be a fleet-wide outage with no preview and
no migration path.

What v4 changes
---------------
Two step ids: ``agent-assign``/``agent-execute`` become
``partition``/``implement-parallel``. The count stays eleven and the order stays
the same, so the document's shape -- arrow chain plus Step table -- is unchanged
and the same order checks apply.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
GRILL_CORE = HERE.parent
SCRIPTS = HERE.parents[1]
ASSETS = HERE.parents[2] / "assets"


def sibling(name: str, directory: Path = SCRIPTS):
    """Load a sibling module by path, the way ``workflow_v3.sibling`` does."""
    return _v3.sibling(name, directory)


def _load_v3():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "grill_core_workflow_v3_for_v4", GRILL_CORE / "workflow_v3.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_v3 = _load_v3()

# Version-agnostic machinery, reused rather than reimplemented. Copying these
# would let v3 and v4 drift on atomicity and diffing, which is exactly where a
# migration must not drift.
Failure = _v3.Failure
Detection = _v3.Detection
Gate = _v3.Gate
JsonParser = _v3.JsonParser
digest = _v3.digest
resolve_root = _v3.resolve_root
load_workflow = _v3.load_workflow
unified_diff = _v3.unified_diff
atomic_replace = _v3.atomic_replace
fsync_directory = _v3.fsync_directory
marker_version = _v3.marker_version
EXIT_OK = _v3.EXIT_OK
EXIT_NO_GO = _v3.EXIT_NO_GO
EXIT_BLOCKED = _v3.EXIT_BLOCKED

TEMPLATE_V4 = ASSETS / "WORKFLOW.v4.template.md"
REGISTRY = ASSETS / "workflow-step-skills.v4.json"
REGISTRY_REF = "assets/workflow-step-skills.v4.json"
REGISTRY_SHA256_PLACEHOLDER = _v3.REGISTRY_SHA256_PLACEHOLDER
PIN_ANCHOR_RE = _v3.PIN_ANCHOR_RE
_CYCLE_HEADING_RE = _v3._CYCLE_HEADING_RE
_TABLE_STEP_RE = _v3._TABLE_STEP_RE

VERSION = "v4"
MARKER = "grill-with-docs-workflow:v4"
SCHEMA = "grill-workflow-migration/v1"

# NEW allowlist. Never derived from workflow_v3.ESSENTIAL at runtime: the two
# tuples must be able to drift without one silently rewriting the other.
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
    "workflow-step-skills.v4.json",
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
)

CANONICAL_STEP_ORDER = (
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
)
STEP_ORDER_MISSING = _v3.STEP_ORDER_MISSING
_STEP_TOKEN_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(step) for step in CANONICAL_STEP_ORDER) + r")(?![\w-])"
)


def registry_state() -> tuple[bytes, str]:
    raw = REGISTRY.read_bytes()
    return raw, "sha256:" + hashlib.sha256(raw).hexdigest()


def pinned_registry_sha256(text: str) -> str | None:
    match = PIN_ANCHOR_RE.search(text)
    return None if match is None else match.group(1)


def pin_is_current(text: str) -> bool:
    """Whether the document pins the live v4 registry digest.

    Checked on READ, not only at migration-write time: a materialised document
    that still carries the unrendered placeholder, or that pins a digest the
    registry no longer has, is a document promising a hash it cannot honour.
    """
    pinned = pinned_registry_sha256(text)
    if pinned is None or pinned == REGISTRY_SHA256_PLACEHOLDER:
        return False
    try:
        _, current = registry_state()
    except OSError:
        return False
    return pinned == current


def render_v4(template_text: str | None = None) -> bytes:
    """Bake the live registry digest into the bundled template."""
    text = TEMPLATE_V4.read_text(encoding="utf-8") if template_text is None else template_text
    if text.count(REGISTRY_SHA256_PLACEHOLDER) != 1:
        raise Failure("TEMPLATE_INVALID", "v4 template must carry exactly one registry placeholder")
    _, current = registry_state()
    return text.replace(REGISTRY_SHA256_PLACEHOLDER, current).encode("utf-8")


def canonical_step_order(text: str) -> bool:
    """Whether every explicit full execution sequence is in canonical v4 order.

    Same shape rule v3 applies, against the v4 order: a document may drop the
    managed marker and the template's whitespace, but it may not declare the
    cycle twice and contradict itself, and it may not reorder the steps in
    either the arrow chain or the Step table.
    """
    match = _CYCLE_HEADING_RE.search(text)
    if match is None:
        return False
    cycle = match.group("body")
    found_sequence = False

    arrow_block: list[str] = []
    for line in [*cycle.splitlines(), ""]:
        if "→" in line:
            arrow_block.append(line)
            continue
        if not arrow_block:
            continue
        steps = tuple(_STEP_TOKEN_RE.findall("\n".join(arrow_block)))
        if steps != CANONICAL_STEP_ORDER:
            return False
        found_sequence = True
        arrow_block = []

    table_steps = tuple(s for s in _TABLE_STEP_RE.findall(cycle) if s in CANONICAL_STEP_ORDER)
    if table_steps:
        if len(table_steps) != len(CANONICAL_STEP_ORDER) or set(table_steps) != set(CANONICAL_STEP_ORDER):
            return False
        found_sequence = True
        if table_steps != CANONICAL_STEP_ORDER:
            return False

    return found_sequence


def compatible_v4(text: str) -> bool:
    return bool(text.strip()) and all(item in text for item in ESSENTIAL) and canonical_step_order(text)


def missing_v4(text: str) -> tuple[str, ...]:
    missing = [item for item in ESSENTIAL if item not in text]
    if not canonical_step_order(text):
        missing.append(STEP_ORDER_MISSING)
    return tuple(missing)


def detect_text(text: str) -> Detection:
    """Classify one workflow document against the v4 frontier."""
    marker = marker_version(text)
    return Detection(marker, marker or None, _v3.compatible_v2(text), compatible_v4(text), missing_v4(text))


def execution_gate(text: str) -> Gate:
    """v4 execution gate: declares the frontier AND pins the live v4 registry."""
    detection = detect_text(text)
    if detection.marker not in (None, VERSION):
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", detection.missing_v3)
    if not detection.v3_compatible:
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", detection.missing_v3)
    if not pin_is_current(text):
        return Gate("BLOCKED", "REGISTRY_PIN_DIVERGENT", ())
    return Gate("OK", None, ())


def v3_gate(text: str) -> Gate:
    """A v3 document stays valid for v3 regardless of the v4 allowlist."""
    return _v3.execution_gate(text)


def runtime_wired() -> bool:
    """Whether the live ``ensure_workflow.py`` actually accepts a v4 document.

    Asks the real production reader, the same way ``workflow_v3.runtime_wired``
    does, rather than comparing version strings against a constant that pins
    what fresh bootstrap materialises.
    """
    ensure = sibling("ensure_workflow")
    return VERSION in getattr(ensure, "EXECUTABLE_MARKER_VERSIONS", ())


def bundled_template() -> bytes:
    return render_v4()


def detect_command(root_argument: str | Path) -> tuple[dict, int]:
    root = resolve_root(root_argument)
    # load_workflow returns (path, bytes, TEXT) -- the third element is the
    # decoded document, not a digest. Hash the bytes explicitly.
    path, raw, text = load_workflow(root)
    current = digest(raw)
    detection = detect_text(text)
    gate = execution_gate(text)
    return {
        "schema": SCHEMA,
        "verdict": gate.status,
        "code": gate.code,
        "path": str(path.relative_to(root)),
        "sha256": current,
        "marker": detection.marker,
        "v2_compatible": detection.v2_compatible,
        "v4_compatible": detection.v3_compatible,
        "missing": list(detection.missing_v3),
        "registry_ref": REGISTRY_REF,
        "registry_sha256": registry_state()[1],
        "pinned_registry_sha256": pinned_registry_sha256(text),
        "runtime_wired": runtime_wired(),
    }, EXIT_OK if gate.status == "OK" else EXIT_BLOCKED


def migrate_command(root_argument: str | Path, *, apply: bool = False,
                    expected_sha256: str | None = None,
                    allow_local_edits: bool = False) -> tuple[dict, int]:
    """Preview-first, no-clobber migration of a v2/v3 document to v4.

    ``--apply`` refuses without ``--expected-sha256`` (compare-and-swap against
    the bytes the preview was computed from) and refuses a document that is not
    a pristine managed template unless ``--allow-local-edits`` says the caller
    looked at the diff and accepts losing those edits.
    """
    root = resolve_root(root_argument)
    path, raw, text = load_workflow(root)
    current = digest(raw)
    target = render_v4()
    preview = {
        "schema": SCHEMA,
        "path": str(path.relative_to(root)),
        "from_version": marker_version(text),
        "to_version": VERSION,
        "sha256": current,
        "target_sha256": digest(target),
        "diff": unified_diff(text, target.decode("utf-8")),
    }
    if compatible_v4(text) and pin_is_current(text):
        return {**preview, "verdict": "REUSED", "code": None}, EXIT_OK
    if not apply:
        return {**preview, "verdict": "PREVIEW", "code": None}, EXIT_OK
    if not runtime_wired():
        return {**preview, "verdict": "BLOCKED", "code": "V4_RUNTIME_NOT_WIRED"}, EXIT_BLOCKED
    if expected_sha256 is None:
        return {**preview, "verdict": "BLOCKED", "code": "EXPECTED_SHA256_REQUIRED"}, EXIT_BLOCKED
    if expected_sha256 != current:
        return {**preview, "verdict": "BLOCKED", "code": "WORKFLOW_CHANGED"}, EXIT_BLOCKED
    pristine = raw == _v3.read_v2_template() or raw == _v3.bundled_template()[0]
    if not pristine and not allow_local_edits:
        return {**preview, "verdict": "BLOCKED", "code": "WORKFLOW_LOCAL_EDITS"}, EXIT_BLOCKED
    atomic_replace(path, target, raw)
    return {**preview, "verdict": "APPLIED", "code": None, "sha256": digest(target)}, EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WORKFLOW.md v4 detection and migration")
    sub = parser.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("detect")
    detect.add_argument("root")
    migrate = sub.add_parser("migrate")
    migrate.add_argument("root")
    migrate.add_argument("--apply", action="store_true")
    migrate.add_argument("--expected-sha256")
    migrate.add_argument("--allow-local-edits", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "detect":
            payload, code = detect_command(args.root)
        else:
            payload, code = migrate_command(
                args.root, apply=args.apply, expected_sha256=args.expected_sha256,
                allow_local_edits=args.allow_local_edits,
            )
    except Failure as failure:
        payload, code = {"schema": SCHEMA, "verdict": "BLOCKED", "code": failure.code,
                         "error": str(failure)}, EXIT_BLOCKED
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
