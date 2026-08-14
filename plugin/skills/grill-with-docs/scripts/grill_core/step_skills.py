#!/usr/bin/env python3
"""Registry ``workflow-step-skills/v1`` and the fail-closed step -> skill resolver.

Plan sections implemented here (v3 gauntlet plan):

* 4.1  -- registry with exactly one entry per Spec Kit vertex, logical identity,
          ``resolve_workflow_skill``, ``skill_resolution_sha256`` and the literal
          ``skill_invocation_key`` formula, plus the ``skill-invocation/v1`` envelope.
* 22 "Workflow -> skill canonica" -- every fail-closed branch listed there.
* 23 -- no ``DIRECT|EMULATED|BEST_EFFORT`` fallback ever leaves this module.

Hard constraints honoured: standard library only, no network, no dependency on a
real ``specify``/``node``/``backlogctl``. Every runtime observation arrives as an
injected catalogue document, so the resolver is pure data in / pure data out.

This module is internal (``grill_core``). The public CLI reaches it only
indirectly through the V3 checkpoint attestation boundary; it never resolves
or dispatches a skill itself.

Round-2 repair (LD-005 reduced scope -- registry, resolver, invocation
correlation only; the attestation chain of dispatch-intent/step-output and
STATE_DIVERGENCE/STALE_OUTPUT belongs to piece F):

* the digest a catalogue must match to be trusted now comes from versioned
  bytes on disk (``assets/workflow-trusted-catalogs.json``), read by
  ``resolve_workflow_skill`` by default -- never from a ``Mapping`` the caller
  assembles at call time (round-2 findings: gaps 1 and 4);
* ``validate_skill_invocation`` anchors every ``skill-resolution/v1`` it is
  handed against the registry itself before trusting it as proof of anything,
  and requires the caller's own expected ``project_id``/``work_item_id``/
  ``run_id``/``attempt_id`` to correlate the receipt against (round-2 findings:
  the ``totally.made.up``/``rm-rf-slash`` forgery, and ``work-999``/``run-999``/
  ``attempt-001``/``proj-999`` all being accepted);
* ``persist_skill_resolution``/``load_persisted_skill_resolution`` give this
  module its own atomic write path for the ``skill-resolution/v1`` document
  4.1 says the core "persists" -- LD-003 forbids editing ``grill_workspace.py``,
  not writing inside ``grill_core``.

Phase 0 (4.1: "resolver os IDs/entrypoints reais de cada runtime e
congela-los nas fixtures antes da implementacao") only ever observed a real,
native entrypoint for the ``claude`` runtime -- ``tests/fixtures/workflow-step-
skills/claude-catalog.json``, captured read-only from ``.claude/skills``. No
Hermes or Codex installation was reachable to observe from this environment,
so every step is honestly ``resolved=false``/``RUNTIME_ENTRYPOINT_UNPROVEN``
for both runtimes rather than a fabricated entrypoint. See
``tests/fixtures/workflow-step-skills/README.md``.

Round-3 repair (LD-005 scope: registry, resolver, invocation correlation --
the round-2 anchor re-derived only IDENTITY facts and never re-checked the
CONTENT a resolution attests):

* ``validate_skill_invocation`` now takes the authorized ``catalog`` (mandatory
  keyword-only) and, inside ``_anchor_resolution_to_registry``, RECOMPUTES the
  resolution the same way ``resolve_workflow_skill`` would for the presented
  ``(step_id, runtime)`` and requires the presented ``skill_resolution_sha256``
  to equal the recomputed one. One equality check covers every field at once
  -- ``skill_content_sha256``, ``skill_manifest_sha256``, ``skill_version``,
  ``minimum_version``, ``source_ref`` and ``catalog.{catalog_id,sha256}`` --
  instead of a hand-picked allowlist that leaked a new field every round
  (round-3 finding: a resolution for ship/claude that kept step_id, skill_id,
  runtime, adapter, entrypoint and entrypoint_kind correct, then re-sealed
  ``skill_content_sha256=sha256:999...``, ``skill_manifest_sha256=
  sha256:888...``, ``skill_version=99.0.0``, ``source_ref="evil@99.0.0"``,
  ``minimum_version="0.0.1"`` and ``catalog={"catalog_id":"attacker-catalog",
  ...,"authorized":true}``, was accepted as attestation for a COMPLETED ``ship``
  receipt -- see ``scratchpad/atk/a5.py``);
* the catalogue trust pin is no longer a ``Mapping`` a caller assembles in
  memory: ``resolve_workflow_skill``'s ``trusted_catalogs`` parameter is
  replaced by ``trusted_catalogs_path`` (round-3 finding: mutating a catalogue
  entry, recomputing ``catalog_sha256`` and passing a matching
  ``trusted_catalogs={...}`` Mapping back in as "authorized" resolved
  successfully -- see ``scratchpad/atk/a3.py``, variant 3b). The default
  (``None``) still loads the versioned asset from disk; a caller who needs a
  different trust configuration (tests only) must point at real bytes on disk,
  not hand the function a dict.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

REGISTRY_SCHEMA = "workflow-step-skills/v1"
RESOLUTION_SCHEMA = "skill-resolution/v1"
INVOCATION_SCHEMA = "skill-invocation/v1"
CATALOG_SCHEMA = "skill-catalog/v1"
TRUSTED_CATALOGS_SCHEMA = "workflow-trusted-catalogs/v1"

WORKFLOW_VERSION = "v3"
RESOLVER_VERSION = "1.0.0"

#: The one and only execution mode a resolved step may carry (plan 4.1).
EXECUTION_MODE = "CANONICAL_SKILL"
#: Modes the plan forbids outright. They must never appear in any document
#: produced here; they exist only so callers and tests can assert their absence.
FORBIDDEN_EXECUTION_MODES = ("DIRECT", "EMULATED", "BEST_EFFORT")

#: Fail-closed verdict codes. The plan (4.1 / 22 / 23) writes them in
#: SCREAMING_SNAKE; the live v2 CLI uses SCREAMING-KEBAB. This module emits the
#: plan literals because the barra names them verbatim; translation to the CLI
#: vocabulary belongs to the wiring round, not here.
BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"
STALE_SKILL_RESOLUTION = "STALE_SKILL_RESOLUTION"
#: A ``skill-invocation/v1`` envelope that does not correlate with the
#: ``skill-resolution/v1`` it claims to attest -- another step, skill, runtime,
#: adapter or entrypoint (plan 22, bullet 7: "receipt de outro step/skill/work
#: item/run/attempt/runtime ... falha"). The envelope may be internally
#: self-consistent (its own key/digest check out) and still be a lie about what
#: was actually resolved and dispatched.
UNATTESTED_STEP_OUTPUT = "UNATTESTED_STEP_OUTPUT"

#: The 11 Spec Kit vertices, byte-identical to ``grill_workspace.SEQUENCE``,
#: ``grill_status.SEQUENCE`` and ``assets/state.template.json``.
SEQUENCE = (
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "agent-assign",
    "agent-execute",
    "converge",
    "verify",
    "review",
    "ship",
)

RUNTIMES = ("hermes", "claude", "codex")
ENTRYPOINT_KINDS = ("skill", "command")
INVOCATION_STATUSES = ("STARTED", "COMPLETED", "FAILED", "BLOCKED")

#: Reasons a registry entry may declare itself unresolved for a runtime.
#: ``RUNTIME_ENTRYPOINT_UNPROVEN`` is the honest default: phase 0 could not
#: observe a native entrypoint for that runtime, so the step must block.
UNRESOLVED_REASONS = (
    "RUNTIME_ENTRYPOINT_UNPROVEN",
    "RUNTIME_UNSUPPORTED",
    "SKILL_NOT_PUBLISHED",
)

ASSETS = Path(__file__).resolve().parents[2] / "assets"
REGISTRY_PATH = ASSETS / "workflow-step-skills.json"
TRUSTED_CATALOGS_PATH = ASSETS / "workflow-trusted-catalogs.json"

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9]+([.-][a-z0-9]+)*$")
ENTRYPOINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
FREE_REF_RE = re.compile(r"^[\x21-\x7e]([\x20-\x7e]{0,254})$")

#: I-JSON safe integer domain (plan 7.4.1 item 1).
MAX_SAFE_INT = 2 ** 53 - 1
MIN_SAFE_INT = -MAX_SAFE_INT

_REGISTRY_KEYS = ("schema", "workflow_version", "registry_version", "runtimes", "steps")
_STEP_KEYS = (
    "skill_id",
    "proposed_skill_id",
    "required",
    "human_authorization_required",
    "allowed_entrypoints",
    "resolutions",
)
_RESOLVED_KEYS = (
    "resolved",
    "adapter",
    "entrypoint",
    "entrypoint_kind",
    "minimum_version",
    "source_ref",
    "catalog_id",
)
_UNRESOLVED_KEYS = ("resolved", "unresolved_reason")
_CATALOG_KEYS = ("schema", "runtime", "catalog_id", "catalog_sha256", "entries")
_TRUSTED_CATALOGS_KEYS = ("schema", "workflow_version", "catalogs")
_CATALOG_ENTRY_KEYS = (
    "entrypoint",
    "entrypoint_kind",
    "adapter",
    "version",
    "source_ref",
    "manifest_sha256",
    "content_sha256",
    "native_invocation",
    "preflight_ref",
)
_INVOCATION_KEYS = (
    "schema",
    "skill_invocation_key",
    "project_id",
    "work_item_id",
    "run_id",
    "step_id",
    "skill_id",
    "skill_version",
    "skill_content_sha256",
    "registry_sha256",
    "skill_resolution_sha256",
    "runtime",
    "adapter",
    "entrypoint",
    "dispatch_key",
    "attempt_id",
    "recovery_generation_id",
    "plan_revision",
    "input_fingerprint",
    "started_receipt_ref",
    "status",
    "output_manifest_sha256",
    "content_sha256",
)
_INVOCATION_KEY_FIELDS = (
    "project_id",
    "work_item_id",
    "run_id",
    "step_id",
    "recovery_generation_id",
    "plan_revision",
    "skill_resolution_sha256",
    "dispatch_key",
)


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------


class SkillResolutionError(Exception):
    """Fail-closed outcome. ``code`` is one of BLOCKED_CAPABILITY,
    STALE_SKILL_RESOLUTION or UNATTESTED_STEP_OUTPUT."""

    def __init__(self, code: str, reason: str, **detail: Any) -> None:
        super().__init__(f"{code}/{reason}")
        self.code = code
        self.reason = reason
        self.detail = detail

    def payload(self) -> dict[str, Any]:
        out: dict[str, Any] = {"verdict": "BLOCKED", "code": self.code, "reason": self.reason}
        if self.detail:
            out["detail"] = {k: self.detail[k] for k in sorted(self.detail)}
        return out


def _blocked(reason: str, **detail: Any) -> SkillResolutionError:
    return SkillResolutionError(BLOCKED_CAPABILITY, reason, **detail)


def _stale(reason: str, **detail: Any) -> SkillResolutionError:
    return SkillResolutionError(STALE_SKILL_RESOLUTION, reason, **detail)


def _unattested(reason: str, **detail: Any) -> SkillResolutionError:
    return SkillResolutionError(UNATTESTED_STEP_OUTPUT, reason, **detail)


class CanonicalizationError(ValueError):
    """The value or the bytes are outside the strict I-JSON / JCS domain."""


# --------------------------------------------------------------------------
# RFC 8785 (JCS) canonicalization + strict I-JSON parsing
# --------------------------------------------------------------------------


def _jcs_string(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:  # lone surrogate
        raise CanonicalizationError("string is not encodable as UTF-8") from exc
    return json.dumps(value, ensure_ascii=False)


def _jcs_number(value: int) -> str:
    if not (MIN_SAFE_INT <= value <= MAX_SAFE_INT):
        raise CanonicalizationError("integer outside the I-JSON safe domain")
    return str(value)


def jcs(value: Any) -> bytes:
    """Serialize ``value`` per RFC 8785 and return the UTF-8 bytes.

    Deliberately narrower than RFC 8785: floats are rejected. No schema in this
    module carries one, and ECMAScript number formatting is the classic source of
    cross-runtime hash drift, so the safe move is to fail closed.
    """
    return _jcs(value).encode("utf-8")


def _jcs(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return _jcs_number(value)
    if isinstance(value, float):
        raise CanonicalizationError("floats are refused; use integers or strings")
    if isinstance(value, str):
        return _jcs_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs(item) for item in value) + "]"
    if isinstance(value, Mapping):
        keys = list(value.keys())
        if any(not isinstance(k, str) for k in keys):
            raise CanonicalizationError("object keys must be strings")
        if len(set(keys)) != len(keys):
            raise CanonicalizationError("duplicate object key")
        ordered = sorted(keys, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(f"{_jcs_string(k)}:{_jcs(value[k])}" for k in ordered) + "}"
    raise CanonicalizationError(f"unsupported type {type(value).__name__}")


def sha256_jcs(value: Any) -> str:
    """``sha256:`` + 64 lowercase hex over the JCS bytes (plan 7.4.1 item 4)."""
    return "sha256:" + hashlib.sha256(jcs(value)).hexdigest()


def _no_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, val in pairs:
        if key in seen:
            raise CanonicalizationError(f"duplicate object key: {key}")
        seen[key] = val
    return seen


def _reject_constant(text: str) -> Any:
    raise CanonicalizationError(f"non I-JSON number literal: {text}")


def parse_strict(data: bytes) -> Any:
    """Strict I-JSON parse: UTF-8, no BOM, no duplicate keys, no NaN/Infinity."""
    if not isinstance(data, (bytes, bytearray)):
        raise CanonicalizationError("strict parse needs bytes")
    if data.startswith(b"\xef\xbb\xbf"):
        raise CanonicalizationError("byte order mark is refused")
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalizationError("payload is not valid UTF-8") from exc
    try:
        return json.loads(
            text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant, parse_float=_reject_float
        )
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(f"malformed JSON: {exc.msg}") from exc


def _reject_float(text: str) -> Any:
    raise CanonicalizationError(f"floating point number is refused: {text}")


# --------------------------------------------------------------------------
# small validators
# --------------------------------------------------------------------------


def _require(condition: Any, reason: str, **detail: Any) -> None:
    if not condition:
        raise _blocked(reason, **detail)


def _exact_keys(value: Any, expected: Iterable[str], reason: str, **detail: Any) -> None:
    _require(isinstance(value, dict), reason, **detail, problem="not an object")
    got = set(value)
    want = set(expected)
    if got != want:
        raise _blocked(
            reason,
            **detail,
            missing=sorted(want - got),
            unexpected=sorted(got - want),
        )


def _text(value: Any, pattern: re.Pattern[str], reason: str, **detail: Any) -> str:
    _require(isinstance(value, str) and bool(pattern.fullmatch(value)), reason, **detail, value=value)
    return value


def version_tuple(value: Any) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise _blocked("INVALID_VERSION", value=value)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------


def load_registry(path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Read, validate and hash the registry. Returns ``(document, registry_sha256)``."""
    target = REGISTRY_PATH if path is None else Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise _blocked("REGISTRY_UNREADABLE", path=target.name) from exc
    return parse_and_hash_registry(raw)


def parse_and_hash_registry(raw: bytes) -> tuple[dict[str, Any], str]:
    """Strict-parse, validate and hash raw registry bytes. Returns ``(document,
    registry_sha256)`` where the hash is computed by :func:`registry_sha256` --
    i.e. over ``raw`` itself, never over a re-serialization of the parsed value.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise _blocked("REGISTRY_INVALID", problem="registry bytes required")
    digest = registry_sha256(raw)
    try:
        document = parse_strict(raw)
    except CanonicalizationError as exc:
        raise _blocked("REGISTRY_INVALID", problem=str(exc)) from exc
    validate_registry(document)
    return document, digest


def registry_sha256(raw: bytes) -> str:
    """LD-001: ``registry_sha256`` is the SHA-256 of the registry asset's literal
    on-disk bytes -- the same string ``sha256sum workflow-step-skills.json``
    prints, no JCS or any other re-serialization involved. ``WORKFLOW.md`` and
    hooks publish this string for humans and agents to check directly.

    JCS stays the canonicalization for *generated* documents (``skill-resolution
    /v1``, ``skill-invocation/v1``, the catalogue digest) -- never for this
    versioned asset. See ``sha256_jcs`` for that other, unrelated, digest.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise _blocked("REGISTRY_INVALID", problem="registry bytes required")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_registry(document: Any) -> dict[str, Any]:
    """Full schema + logical-identity validation. Raises BLOCKED_CAPABILITY."""
    _exact_keys(document, _REGISTRY_KEYS, "REGISTRY_INVALID")
    _require(document["schema"] == REGISTRY_SCHEMA, "REGISTRY_SCHEMA", value=document["schema"])
    _require(
        document["workflow_version"] == WORKFLOW_VERSION,
        "REGISTRY_WORKFLOW_VERSION",
        value=document["workflow_version"],
    )
    _text(document["registry_version"], re.compile(r"^[1-9][0-9]*$"), "REGISTRY_VERSION")
    _require(document["runtimes"] == list(RUNTIMES), "REGISTRY_RUNTIMES", value=document["runtimes"])

    steps = document["steps"]
    _require(isinstance(steps, dict), "REGISTRY_STEPS", problem="not an object")
    order = tuple(steps)
    if order != SEQUENCE:
        raise _blocked(
            "REGISTRY_STEP_SET",
            expected=list(SEQUENCE),
            got=list(order),
            missing=sorted(set(SEQUENCE) - set(order)),
            unexpected=sorted(set(order) - set(SEQUENCE)),
        )

    skill_ids: dict[str, str] = {}
    entrypoints: dict[tuple[str, str], str] = {}
    for step_id in SEQUENCE:
        entry = steps[step_id]
        _exact_keys(entry, _STEP_KEYS, "REGISTRY_STEP_INVALID", step_id=step_id)
        skill_id = _text(entry["skill_id"], ID_RE, "REGISTRY_SKILL_ID", step_id=step_id)
        _text(entry["proposed_skill_id"], ID_RE, "REGISTRY_PROPOSED_SKILL_ID", step_id=step_id)
        if skill_id in skill_ids:
            raise _blocked("REGISTRY_DUPLICATE_SKILL_ID", skill_id=skill_id, steps=[skill_ids[skill_id], step_id])
        skill_ids[skill_id] = step_id

        _require(entry["required"] is True, "REGISTRY_STEP_NOT_REQUIRED", step_id=step_id)
        _require(
            isinstance(entry["human_authorization_required"], bool),
            "REGISTRY_HUMAN_AUTHORIZATION",
            step_id=step_id,
        )
        _require(
            entry["human_authorization_required"] is (step_id == "ship"),
            "REGISTRY_HUMAN_AUTHORIZATION",
            step_id=step_id,
        )

        allowed = entry["allowed_entrypoints"]
        _require(isinstance(allowed, list) and allowed, "REGISTRY_ALLOWED_ENTRYPOINTS", step_id=step_id)
        _require(len(set(allowed)) == len(allowed), "REGISTRY_ALLOWED_ENTRYPOINTS", step_id=step_id)
        _require(
            all(kind in ENTRYPOINT_KINDS for kind in allowed),
            "REGISTRY_ALLOWED_ENTRYPOINTS",
            step_id=step_id,
            value=allowed,
        )

        resolutions = entry["resolutions"]
        _exact_keys(resolutions, RUNTIMES, "REGISTRY_RESOLUTIONS", step_id=step_id)
        for runtime in RUNTIMES:
            _validate_resolution(step_id, runtime, resolutions[runtime], allowed, entrypoints)
    return document


def _validate_resolution(
    step_id: str,
    runtime: str,
    resolution: Any,
    allowed: Sequence[str],
    entrypoints: dict[tuple[str, str], str],
) -> None:
    _require(isinstance(resolution, dict), "REGISTRY_RESOLUTION_INVALID", step_id=step_id, runtime=runtime)
    _require(
        isinstance(resolution.get("resolved"), bool),
        "REGISTRY_RESOLUTION_INVALID",
        step_id=step_id,
        runtime=runtime,
        problem="resolved must be a boolean",
    )
    if not resolution["resolved"]:
        _exact_keys(resolution, _UNRESOLVED_KEYS, "REGISTRY_RESOLUTION_INVALID", step_id=step_id, runtime=runtime)
        _require(
            resolution["unresolved_reason"] in UNRESOLVED_REASONS,
            "REGISTRY_UNRESOLVED_REASON",
            step_id=step_id,
            runtime=runtime,
            value=resolution["unresolved_reason"],
        )
        return

    _exact_keys(resolution, _RESOLVED_KEYS, "REGISTRY_RESOLUTION_INVALID", step_id=step_id, runtime=runtime)
    _text(resolution["adapter"], FREE_REF_RE, "REGISTRY_ADAPTER", step_id=step_id, runtime=runtime)
    entrypoint = _text(resolution["entrypoint"], ENTRYPOINT_RE, "REGISTRY_ENTRYPOINT", step_id=step_id, runtime=runtime)
    kind = resolution["entrypoint_kind"]
    _require(kind in ENTRYPOINT_KINDS, "REGISTRY_ENTRYPOINT_KIND", step_id=step_id, runtime=runtime, value=kind)
    _require(kind in allowed, "REGISTRY_ENTRYPOINT_KIND", step_id=step_id, runtime=runtime, value=kind)
    version_tuple(resolution["minimum_version"])
    _text(resolution["source_ref"], FREE_REF_RE, "REGISTRY_SOURCE_REF", step_id=step_id, runtime=runtime)
    _text(resolution["catalog_id"], ID_RE, "REGISTRY_CATALOG_ID", step_id=step_id, runtime=runtime)

    key = (runtime, entrypoint)
    if key in entrypoints:
        raise _blocked(
            "REGISTRY_DUPLICATE_ENTRYPOINT",
            runtime=runtime,
            entrypoint=entrypoint,
            steps=[entrypoints[key], step_id],
        )
    entrypoints[key] = step_id


# --------------------------------------------------------------------------
# runtime catalogue (injected observation, never fetched)
# --------------------------------------------------------------------------


def validate_catalog(catalog: Any) -> dict[str, Any]:
    _exact_keys(catalog, _CATALOG_KEYS, "CATALOG_INVALID")
    _require(catalog["schema"] == CATALOG_SCHEMA, "CATALOG_SCHEMA", value=catalog["schema"])
    _require(catalog["runtime"] in RUNTIMES, "CATALOG_RUNTIME", value=catalog["runtime"])
    _text(catalog["catalog_id"], ID_RE, "CATALOG_ID")
    _text(catalog["catalog_sha256"], SHA256_RE, "CATALOG_DIGEST")
    entries = catalog["entries"]
    _require(isinstance(entries, list) and entries, "CATALOG_ENTRIES", problem="empty or not a list")
    for index, entry in enumerate(entries):
        _exact_keys(entry, _CATALOG_ENTRY_KEYS, "CATALOG_ENTRY_INVALID", index=index)
        _text(entry["entrypoint"], ENTRYPOINT_RE, "CATALOG_ENTRY_INVALID", index=index)
        _require(
            entry["entrypoint_kind"] in ENTRYPOINT_KINDS,
            "CATALOG_ENTRY_INVALID",
            index=index,
            problem="entrypoint_kind",
        )
        _text(entry["adapter"], FREE_REF_RE, "CATALOG_ENTRY_INVALID", index=index)
        version_tuple(entry["version"])
        _text(entry["source_ref"], FREE_REF_RE, "CATALOG_ENTRY_INVALID", index=index)
        _text(entry["manifest_sha256"], SHA256_RE, "INVALID_DIGEST", index=index, field="manifest_sha256")
        _text(entry["content_sha256"], SHA256_RE, "INVALID_DIGEST", index=index, field="content_sha256")
        _require(
            isinstance(entry["native_invocation"], bool),
            "CATALOG_ENTRY_INVALID",
            index=index,
            problem="native_invocation",
        )
        _text(entry["preflight_ref"], FREE_REF_RE, "CATALOG_ENTRY_INVALID", index=index)

    # The catalogue self-declares its own digest in ``catalog_sha256``; a trusted
    # caller only compares THAT declared string against ``trusted_catalogs``
    # (see resolve_workflow_skill below). Nothing before this point ever checks
    # the declared digest against the entries actually present -- an attacker who
    # mutates entries while keeping the old, still-authorized digest sails
    # through untouched (round-1 finding: probe1). Recompute it here, over the
    # exact entries just validated, before any caller can read a single field
    # out of them.
    expected_catalog_sha256 = sha256_jcs(entries)
    if expected_catalog_sha256 != catalog["catalog_sha256"]:
        raise _blocked(
            "CATALOG_CONTENT_MISMATCH",
            catalog_id=catalog.get("catalog_id"),
            declared=catalog["catalog_sha256"],
            computed=expected_catalog_sha256,
        )
    return catalog


# --------------------------------------------------------------------------
# trusted catalog digests (versioned pin, never a caller-supplied Mapping)
# --------------------------------------------------------------------------


def _parse_trusted_catalogs(raw: bytes) -> dict[str, str]:
    """Validate one immutable trusted-catalog byte snapshot."""
    try:
        document = parse_strict(raw)
    except CanonicalizationError as exc:
        raise _blocked("TRUSTED_CATALOGS_INVALID", problem=str(exc)) from exc
    _exact_keys(document, _TRUSTED_CATALOGS_KEYS, "TRUSTED_CATALOGS_INVALID")
    _require(
        document["schema"] == TRUSTED_CATALOGS_SCHEMA, "TRUSTED_CATALOGS_SCHEMA", value=document["schema"]
    )
    _require(
        document["workflow_version"] == WORKFLOW_VERSION,
        "TRUSTED_CATALOGS_WORKFLOW_VERSION",
        value=document["workflow_version"],
    )
    catalogs = document["catalogs"]
    _require(isinstance(catalogs, dict) and catalogs, "TRUSTED_CATALOGS_INVALID", problem="catalogs")
    out: dict[str, str] = {}
    for catalog_id, digest in catalogs.items():
        _text(catalog_id, ID_RE, "TRUSTED_CATALOGS_INVALID", field="catalog_id")
        out[catalog_id] = _text(
            digest, SHA256_RE, "TRUSTED_CATALOGS_INVALID", field="catalog_sha256", catalog_id=catalog_id
        )
    return out


def _load_trusted_catalogs_snapshot(path: Path | None = None) -> tuple[bytes, dict[str, str]]:
    """Read and validate one versioned trust snapshot from an asset path."""
    target = TRUSTED_CATALOGS_PATH if path is None else Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise _blocked("TRUSTED_CATALOGS_UNREADABLE", path=target.name) from exc
    return raw, _parse_trusted_catalogs(raw)


def load_trusted_catalogs(path: Path | None = None) -> dict[str, str]:
    """Load the versioned trust asset from disk, never a caller Mapping."""
    return _load_trusted_catalogs_snapshot(path)[1]


# --------------------------------------------------------------------------
# the resolver
# --------------------------------------------------------------------------


def _resolve_workflow_skill(
    step_id: str,
    runtime: str,
    registry_sha256_expected: str,
    *,
    registry: bytes | None = None,
    catalog: Mapping[str, Any] | None = None,
    trusted_catalogs: Mapping[str, str],
    trusted_catalogs_bytes: bytes | None = None,
    pinned_resolution: Mapping[str, Any] | None = None,
    resolver_version: str = RESOLVER_VERSION,
) -> dict[str, Any]:
    """Resolve one Spec Kit step to its canonical skill for ``runtime``.

    ``registry_sha256_expected`` is the caller's pin, exactly as the plan's
    ``resolve_workflow_skill(step_id, runtime, registry_sha256)``. Everything the
    resolver observes about the runtime arrives through ``catalog`` -- there is
    no discovery, no shell-out and no network.

    ``registry``, when given, is the registry asset's raw bytes -- never a
    pre-parsed document. LD-001: ``registry_sha256`` is the SHA-256 of the
    literal bytes on disk, so the resolver must hash the same bytes it parses;
    accepting an already-parsed ``Mapping`` here would let two byte-different
    files collapse onto one digest (round-1 finding: probe2). Omit it to load
    and hash the shipped asset from disk.

    The parsed trust map is internal: public callers use the wrapper below,
    which reads a versioned asset path.  It is never caller-provided.

    Returns a ``skill-resolution/v1`` document. Raises ``SkillResolutionError``
    with ``BLOCKED_CAPABILITY`` or ``STALE_SKILL_RESOLUTION`` otherwise. It never
    returns a DIRECT / EMULATED / BEST_EFFORT fallback.
    """
    document, actual = load_registry() if registry is None else parse_and_hash_registry(registry)
    _text(registry_sha256_expected, SHA256_RE, "INVALID_DIGEST", field="registry_sha256")
    if actual != registry_sha256_expected:
        raise _stale("REGISTRY_SHA256_MISMATCH", expected=registry_sha256_expected, actual=actual)

    if runtime not in RUNTIMES:
        raise _blocked("UNKNOWN_RUNTIME", runtime=runtime)
    if not isinstance(step_id, str) or step_id not in document["steps"]:
        raise _blocked("UNKNOWN_STEP", step_id=step_id)

    step = document["steps"][step_id]
    pinned = step["resolutions"][runtime]
    if not pinned["resolved"]:
        raise _blocked(pinned["unresolved_reason"], step_id=step_id, runtime=runtime)

    if catalog is None:
        raise _blocked("CATALOG_ABSENT", step_id=step_id, runtime=runtime)
    catalog = validate_catalog(catalog)
    if catalog["runtime"] != runtime:
        raise _blocked("CATALOG_RUNTIME_MISMATCH", expected=runtime, got=catalog["runtime"])
    if catalog["catalog_id"] != pinned["catalog_id"]:
        raise _blocked("CATALOG_MISMATCH", expected=pinned["catalog_id"], got=catalog["catalog_id"])

    trusted = trusted_catalogs
    if catalog["catalog_id"] not in trusted:
        raise _blocked("UNTRUSTED_CATALOG", catalog_id=catalog["catalog_id"])
    authorized_digest = trusted[catalog["catalog_id"]]
    _text(authorized_digest, SHA256_RE, "INVALID_DIGEST", field="trusted_catalog_sha256")
    if authorized_digest != catalog["catalog_sha256"]:
        raise _blocked(
            "CATALOG_SHA256_MISMATCH",
            catalog_id=catalog["catalog_id"],
            expected=authorized_digest,
            actual=catalog["catalog_sha256"],
        )

    matches = [entry for entry in catalog["entries"] if entry["entrypoint"] == pinned["entrypoint"]]
    if not matches:
        raise _blocked("ENTRYPOINT_ABSENT", step_id=step_id, runtime=runtime, entrypoint=pinned["entrypoint"])
    if len(matches) > 1:
        raise _blocked(
            "AMBIGUOUS_ENTRYPOINT",
            step_id=step_id,
            runtime=runtime,
            entrypoint=pinned["entrypoint"],
            count=len(matches),
        )
    entry = matches[0]

    if entry["entrypoint_kind"] != pinned["entrypoint_kind"]:
        raise _blocked(
            "ENTRYPOINT_KIND_MISMATCH",
            step_id=step_id,
            expected=pinned["entrypoint_kind"],
            got=entry["entrypoint_kind"],
        )
    if entry["entrypoint_kind"] not in step["allowed_entrypoints"]:
        raise _blocked("ENTRYPOINT_KIND_MISMATCH", step_id=step_id, got=entry["entrypoint_kind"])
    if entry["adapter"] != pinned["adapter"]:
        raise _blocked("ADAPTER_MISMATCH", step_id=step_id, expected=pinned["adapter"], got=entry["adapter"])
    if entry["native_invocation"] is not True:
        raise _blocked("NO_NATIVE_ENTRYPOINT", step_id=step_id, runtime=runtime, entrypoint=entry["entrypoint"])
    if entry["source_ref"] != pinned["source_ref"]:
        raise _blocked("SOURCE_REF_MISMATCH", step_id=step_id, expected=pinned["source_ref"], got=entry["source_ref"])
    if version_tuple(entry["version"]) < version_tuple(pinned["minimum_version"]):
        raise _blocked(
            "VERSION_BELOW_MINIMUM",
            step_id=step_id,
            minimum=pinned["minimum_version"],
            got=entry["version"],
        )

    resolution: dict[str, Any] = {
        "schema": RESOLUTION_SCHEMA,
        "resolver_version": _text(resolver_version, SEMVER_RE, "INVALID_RESOLVER_VERSION"),
        "workflow_version": document["workflow_version"],
        "registry_sha256": actual,
        "step_id": step_id,
        "skill_id": step["skill_id"],
        "required": step["required"],
        "human_authorization_required": step["human_authorization_required"],
        "runtime": runtime,
        "adapter": entry["adapter"],
        "entrypoint": entry["entrypoint"],
        "entrypoint_kind": entry["entrypoint_kind"],
        "execution_mode": EXECUTION_MODE,
        "skill_version": entry["version"],
        "minimum_version": pinned["minimum_version"],
        "source_ref": entry["source_ref"],
        "skill_manifest_sha256": entry["manifest_sha256"],
        "skill_content_sha256": entry["content_sha256"],
        "catalog": {
            "catalog_id": catalog["catalog_id"],
            "sha256": catalog["catalog_sha256"],
            "authorized": True,
        },
        "capability_preflight": {
            "native_invocation": True,
            "preflight_ref": entry["preflight_ref"],
        },
    }

    if pinned_resolution is not None:
        _compare_pinned(resolution, pinned_resolution)

    resolution["skill_resolution_sha256"] = sha256_jcs(resolution)
    return resolution


def resolve_workflow_skill(
    step_id: str,
    runtime: str,
    registry_sha256_expected: str,
    *,
    registry: bytes | None = None,
    catalog: Mapping[str, Any] | None = None,
    trusted_catalogs_path: Path | str | None = None,
    pinned_resolution: Mapping[str, Any] | None = None,
    resolver_version: str = RESOLVER_VERSION,
) -> dict[str, Any]:
    """Resolve one skill against a trust asset path, never caller trust data."""
    trusted = load_trusted_catalogs(
        None if trusted_catalogs_path is None else Path(trusted_catalogs_path)
    )
    return _resolve_workflow_skill(
        step_id,
        runtime,
        registry_sha256_expected,
        registry=registry,
        catalog=catalog,
        trusted_catalogs=trusted,
        pinned_resolution=pinned_resolution,
        resolver_version=resolver_version,
    )


def resolve_shipped_workflow_skills(
    step_ids: tuple[str, ...],
    runtime: str,
    registry_sha256_expected: str,
    *,
    registry: bytes,
    catalog: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bytes]:
    """Resolve a batch using one hardcoded shipped trust-asset snapshot."""
    trusted_bytes, trusted = _load_trusted_catalogs_snapshot()
    return [
        _resolve_workflow_skill(
            step_id,
            runtime,
            registry_sha256_expected,
            registry=registry,
            catalog=catalog,
            trusted_catalogs=trusted,
        )
        for step_id in step_ids
    ], trusted_bytes


#: Fields a persisted preflight resolution pins. Any drift is STALE_SKILL_RESOLUTION.
PINNED_FIELDS = (
    "step_id",
    "skill_id",
    "runtime",
    "adapter",
    "entrypoint",
    "entrypoint_kind",
    "skill_version",
    "source_ref",
    "skill_manifest_sha256",
    "skill_content_sha256",
    "registry_sha256",
)


def _compare_pinned(fresh: Mapping[str, Any], pinned: Mapping[str, Any]) -> None:
    """The preflight pin versus what the catalogue says now (plan 22, bullet 2)."""
    if not isinstance(pinned, Mapping) or pinned.get("schema") != RESOLUTION_SCHEMA:
        raise _stale("PINNED_RESOLUTION_INVALID")
    for field in PINNED_FIELDS:
        if field not in pinned:
            raise _stale("PINNED_RESOLUTION_INVALID", field=field)
        if pinned[field] != fresh[field]:
            raise _stale("SKILL_CHANGED_AFTER_PREFLIGHT", field=field, pinned=pinned[field], actual=fresh[field])
    expected = pinned.get("skill_resolution_sha256")
    if expected is not None:
        body = {k: v for k, v in pinned.items() if k != "skill_resolution_sha256"}
        if sha256_jcs(body) != expected:
            raise _stale("PINNED_RESOLUTION_TAMPERED")


def verify_resolution_digest(resolution: Mapping[str, Any]) -> bool:
    """Recompute ``skill_resolution_sha256`` over the document minus that field."""
    body = {k: v for k, v in resolution.items() if k != "skill_resolution_sha256"}
    return sha256_jcs(body) == resolution.get("skill_resolution_sha256")


# --------------------------------------------------------------------------
# invocation key + envelope (plan 4.1)
# --------------------------------------------------------------------------


def skill_invocation_key(
    project_id: str,
    work_item_id: str,
    run_id: str,
    step_id: str,
    recovery_generation_id: str,
    plan_revision: int,
    skill_resolution_sha256: str,
    dispatch_key: str,
) -> str:
    """``SHA256(JCS(project_id, work_item_id, run_id, step_id, recovery_generation_id,
    plan_revision, skill_resolution_sha256, dispatch_key))`` -- plan 4.1, verbatim.
    """
    for name, value in (
        ("project_id", project_id),
        ("work_item_id", work_item_id),
        ("run_id", run_id),
        ("recovery_generation_id", recovery_generation_id),
    ):
        _text(value, FREE_REF_RE, "INVALID_INVOCATION_INPUT", field=name)
    _require(step_id in SEQUENCE, "INVALID_INVOCATION_INPUT", field="step_id", value=step_id)
    _require(
        isinstance(plan_revision, int) and not isinstance(plan_revision, bool) and plan_revision >= 0,
        "INVALID_INVOCATION_INPUT",
        field="plan_revision",
        value=plan_revision,
    )
    _text(skill_resolution_sha256, SHA256_RE, "INVALID_DIGEST", field="skill_resolution_sha256")
    _text(dispatch_key, SHA256_RE, "INVALID_DIGEST", field="dispatch_key")
    return sha256_jcs(
        {
            "project_id": project_id,
            "work_item_id": work_item_id,
            "run_id": run_id,
            "step_id": step_id,
            "recovery_generation_id": recovery_generation_id,
            "plan_revision": plan_revision,
            "skill_resolution_sha256": skill_resolution_sha256,
            "dispatch_key": dispatch_key,
        }
    )


#: Envelope fields that must equal the ``skill-resolution/v1`` actually used to
#: dispatch it. Plan 22, bullet 7: a receipt "de outro step/skill/work item/run/
#: attempt/runtime" must fail, not just a receipt that forges its own key. The
#: key/digest checks below only prove the envelope is self-consistent; they say
#: nothing about whether it attests the resolution it claims to.
_ATTESTED_FIELDS = (
    "step_id",
    "skill_id",
    "skill_version",
    "skill_content_sha256",
    "registry_sha256",
    "skill_resolution_sha256",
    "runtime",
    "adapter",
    "entrypoint",
)


#: Execution-context fields the caller must supply and the envelope must match
#: exactly. Plan 22, bullet 7: "receipt ... de outro work item/run/attempt"
#: must fail. Round-2 finding: with no expected context ever passed in,
#: envelopes claiming ``work_item_id="work-999"``, ``run_id="run-999"``,
#: ``attempt_id="attempt-001"`` or ``project_id="proj-999"`` were all accepted
#: -- there was no value to compare them against.
_CONTEXT_FIELDS = ("project_id", "work_item_id", "run_id", "attempt_id")


def _anchor_resolution_to_registry(
    resolution: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
    registry: bytes | None = None,
    trusted_catalogs_path: Path | str | None = None,
) -> None:
    """A ``skill-resolution/v1`` is only proof of what the registry actually
    says -- never proof merely because it is internally self-consistent (its
    own key/digest check out).

    Round-2 finding: a resolution with ``skill_id='totally.made.up'``,
    ``entrypoint='rm-rf-slash'``, ``runtime='codex'`` had its
    ``skill_resolution_sha256`` recomputed so it verified cleanly, and the
    ``COMPLETED`` receipt for ``step_id='ship'`` attesting it was accepted --
    while ``resolve_workflow_skill('ship', 'codex', ...)`` blocks with
    ``RUNTIME_ENTRYPOINT_UNPROVEN`` in the very same process. The identity
    checks below (step, skill_id, runtime resolved, adapter/entrypoint/
    entrypoint_kind) catch exactly that.

    Round-3 finding: identity alone is not content. A resolution for
    ship/claude that kept every one of those identity fields correct and only
    re-sealed ``skill_content_sha256``, ``skill_manifest_sha256``,
    ``skill_version``, ``minimum_version``, ``source_ref`` and ``catalog`` was
    still accepted, because nothing compared those fields against anything.
    Comparing them one at a time is an allowlist that leaks a new field every
    round; instead, RECOMPUTE the resolution exactly as
    ``resolve_workflow_skill`` would for this ``(step_id, runtime)`` against
    the same catalogue and trust pin, and require the presented
    ``skill_resolution_sha256`` to equal the recomputed one. One equality
    covers every field in the document at once, including any not yet named
    here.
    """
    document, actual = load_registry() if registry is None else parse_and_hash_registry(registry)
    if resolution.get("registry_sha256") != actual:
        raise _unattested(
            "RESOLUTION_REGISTRY_MISMATCH", expected=actual, actual=resolution.get("registry_sha256")
        )
    step_id = resolution.get("step_id")
    if not isinstance(step_id, str) or step_id not in document["steps"]:
        raise _unattested("RESOLUTION_UNKNOWN_STEP", step_id=step_id)
    step = document["steps"][step_id]
    if resolution.get("skill_id") != step["skill_id"]:
        raise _unattested(
            "RESOLUTION_SKILL_ID_MISMATCH",
            step_id=step_id,
            expected=step["skill_id"],
            actual=resolution.get("skill_id"),
        )
    runtime = resolution.get("runtime")
    if runtime not in RUNTIMES:
        raise _unattested("RESOLUTION_UNKNOWN_RUNTIME", runtime=runtime)
    pinned = step["resolutions"][runtime]
    if not pinned["resolved"]:
        # The registry itself already knows why: reuse its own reason instead
        # of inventing a second vocabulary for the same fact.
        raise _unattested(pinned["unresolved_reason"], step_id=step_id, runtime=runtime)
    for field in ("adapter", "entrypoint", "entrypoint_kind"):
        if resolution.get(field) != pinned[field]:
            raise _unattested(
                "RESOLUTION_REGISTRY_DRIFT",
                step_id=step_id,
                runtime=runtime,
                field=field,
                expected=pinned[field],
                actual=resolution.get(field),
            )

    try:
        recomputed = resolve_workflow_skill(
            step_id,
            runtime,
            actual,
            registry=registry,
            catalog=catalog,
            trusted_catalogs_path=trusted_catalogs_path,
        )
    except SkillResolutionError as exc:
        raise _unattested(
            "RESOLUTION_NOT_REPRODUCIBLE", step_id=step_id, runtime=runtime, registry_reason=exc.reason
        ) from exc
    if resolution.get("skill_resolution_sha256") != recomputed["skill_resolution_sha256"]:
        raise _unattested(
            "RESOLUTION_CONTENT_FORGED",
            step_id=step_id,
            runtime=runtime,
            expected=recomputed["skill_resolution_sha256"],
            actual=resolution.get("skill_resolution_sha256"),
        )


def _correlate_with_resolution(
    document: Mapping[str, Any],
    resolution: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
    registry: bytes | None = None,
    trusted_catalogs_path: Path | str | None = None,
) -> None:
    if not isinstance(resolution, Mapping) or resolution.get("schema") != RESOLUTION_SCHEMA:
        raise _unattested("RESOLUTION_INVALID")
    if not verify_resolution_digest(resolution):
        raise _unattested("RESOLUTION_INVALID", problem="skill_resolution_sha256 does not verify")
    _anchor_resolution_to_registry(
        resolution, catalog=catalog, registry=registry, trusted_catalogs_path=trusted_catalogs_path
    )
    for field in _ATTESTED_FIELDS:
        if field not in resolution:
            raise _unattested("RESOLUTION_INVALID", field=field)
        if document.get(field) != resolution[field]:
            raise _unattested(
                "INVOCATION_RESOLUTION_MISMATCH",
                field=field,
                envelope=document.get(field),
                resolution=resolution[field],
            )


def validate_skill_invocation(
    document: Any,
    resolution: Mapping[str, Any],
    *,
    project_id: str,
    work_item_id: str,
    run_id: str,
    attempt_id: str,
    catalog: Mapping[str, Any],
    registry: bytes | None = None,
    trusted_catalogs_path: Path | str | None = None,
) -> dict[str, Any]:
    """Validate a ``skill-invocation/v1`` envelope, its recomputed key/digest,
    its correlation with the ``skill-resolution/v1`` it claims to attest, and
    that resolution's own anchor to the registered ``(step_id, runtime)`` pair.

    ``resolution`` is mandatory, not an optional cross-check: without it there is
    no way to tell a genuine receipt from one that borrows another step's, skill's
    or runtime's identifiers while staying internally self-consistent (round-1
    finding: probe3 -- a ``step_id="ship"`` envelope carrying ``verify``'s skill
    and hashes validated cleanly because nothing compared it to what was actually
    resolved). Nor is a self-consistent resolution proof by itself (round-2
    finding, see ``_anchor_resolution_to_registry``).

    ``project_id``/``work_item_id``/``run_id``/``attempt_id`` are equally
    mandatory keyword-only arguments -- the caller's own expectation of which
    execution this receipt should belong to. A receipt that is internally
    perfect but correlates with a different work item, run or attempt is
    exactly the round-2 attack (``work-999``/``run-999``/``attempt-001``/
    ``proj-999`` all used to be accepted for lack of anything to compare
    against).

    ``catalog`` is equally mandatory: the anchor recomputes the resolution
    exactly as ``resolve_workflow_skill`` would, from this same catalogue, and
    requires the presented ``skill_resolution_sha256`` to equal the recomputed
    one (round-3 finding, see ``_anchor_resolution_to_registry``). Without a
    catalogue to recompute against, identity can be checked but content
    cannot. ``trusted_catalogs_path`` is optional and, like
    ``resolve_workflow_skill``'s parameter of the same name, defaults to the
    versioned trust asset on disk.
    """
    _exact_keys(document, _INVOCATION_KEYS, "INVOCATION_INVALID")
    _require(document["schema"] == INVOCATION_SCHEMA, "INVOCATION_SCHEMA", value=document["schema"])
    _require(document["status"] in INVOCATION_STATUSES, "INVOCATION_STATUS", value=document["status"])
    _require(document["runtime"] in RUNTIMES, "INVOCATION_RUNTIME", value=document["runtime"])
    _require(document["step_id"] in SEQUENCE, "INVOCATION_STEP", value=document["step_id"])
    for field in (
        "skill_content_sha256",
        "registry_sha256",
        "skill_resolution_sha256",
        "dispatch_key",
        "input_fingerprint",
        "output_manifest_sha256",
        "skill_invocation_key",
        "content_sha256",
    ):
        _text(document[field], SHA256_RE, "INVALID_DIGEST", field=field)
    for mode in FORBIDDEN_EXECUTION_MODES:
        _require(mode not in json.dumps(document), "FORBIDDEN_EXECUTION_MODE", mode=mode)

    # Structural integrity first (key formula, then content hash over the
    # whole body) -- both project_id/work_item_id/run_id and attempt_id are
    # covered by content_sha256, so a document that is internally torn must
    # be caught here before context correlation ever reads a field out of it.
    expected_key = skill_invocation_key(*(document[f] for f in _INVOCATION_KEY_FIELDS))
    if expected_key != document["skill_invocation_key"]:
        raise _stale(
            "INVOCATION_KEY_MISMATCH", expected=expected_key, actual=document["skill_invocation_key"]
        )
    body = {k: v for k, v in document.items() if k != "content_sha256"}
    if sha256_jcs(body) != document["content_sha256"]:
        raise _stale("INVOCATION_CONTENT_MISMATCH")

    expected_context = {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "run_id": run_id,
        "attempt_id": attempt_id,
    }
    for field in _CONTEXT_FIELDS:
        if document.get(field) != expected_context[field]:
            raise _unattested(
                "INVOCATION_CONTEXT_MISMATCH",
                field=field,
                envelope=document.get(field),
                expected=expected_context[field],
            )

    _correlate_with_resolution(
        document, resolution, catalog=catalog, registry=registry, trusted_catalogs_path=trusted_catalogs_path
    )
    return document


# --------------------------------------------------------------------------
# persistence (plan 4.1: "o core executa resolve_workflow_skill(...) e
# persiste skill-resolution/v1"). LD-003 forbids editing grill_workspace.py
# and ensure_workflow.py; it says nothing about writing inside grill_core.
# ``destination`` is entirely the caller's concern -- this module has no
# opinion on work-item/run/attempt path layout, only on writing the document
# durably once it is handed a path.
# --------------------------------------------------------------------------


def persist_skill_resolution(resolution: Mapping[str, Any], destination: str | Path) -> Path:
    """Atomically persist a validated ``skill-resolution/v1`` document.

    Same-directory temp file, ``fsync``, ``os.replace`` -- a crash mid-write
    never leaves a torn file where a reader expects a complete one, and never
    leaves a stray temp file behind on success.
    """
    if not isinstance(resolution, Mapping) or resolution.get("schema") != RESOLUTION_SCHEMA:
        raise _blocked("RESOLUTION_INVALID", problem="not a skill-resolution/v1 document")
    if not verify_resolution_digest(resolution):
        raise _blocked("RESOLUTION_INVALID", problem="skill_resolution_sha256 does not verify")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(dict(resolution), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    tmp = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    with open(tmp, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, destination)
    return destination


def load_persisted_skill_resolution(path: str | Path) -> dict[str, Any]:
    """Read back a document written by :func:`persist_skill_resolution` and
    verify its digest still checks out -- corrupted or hand-edited bytes fail
    closed rather than being trusted because a file merely exists at the
    expected path."""
    raw = Path(path).read_bytes()
    try:
        document = parse_strict(raw)
    except CanonicalizationError as exc:
        raise _blocked("RESOLUTION_INVALID", problem=str(exc)) from exc
    if not isinstance(document, dict) or document.get("schema") != RESOLUTION_SCHEMA:
        raise _blocked("RESOLUTION_INVALID", problem="not a skill-resolution/v1 document")
    if not verify_resolution_digest(document):
        raise _blocked("RESOLUTION_INVALID", problem="skill_resolution_sha256 does not verify")
    return document
