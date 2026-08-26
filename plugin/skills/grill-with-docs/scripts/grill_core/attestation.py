#!/usr/bin/env python3
"""End-to-end attestation chain for the v3 gauntlet plan (LD-005 / "peca F").

Plan sections implemented here:

* 4.1  -- the full chain ``skill-resolution -> dispatch-intent CANONICAL_SKILL
          -> invocation STARTED -> invocation terminal -> step-output``. Any
          file, log, commit, green test or side effect produced without that
          chain is ``UNATTESTED_STEP_OUTPUT`` and never advances
          ``development.sequence``.
* 5.5   -- ``dispatch-intent/v1`` envelope, literal, and the literal
          ``dispatch_key`` formula (excludes attempt/epoch/lease/timestamp).
* 7.1.3 -- ``step-output/v1`` envelope, literal, terminal immutability
          (``FAILED`` is never overwritten by ``COMPLETED``; a retry mints a
          new ``step_execution_id`` linked by ``supersedes_step_execution_id``).
* 22/23 -- the adversarial fixture (direct execution of verify/review/ship
          without invoking the skill) and the "no DIRECT|EMULATED|BEST_EFFORT
          fallback for a required step" invariant.

LD-005: this module is the second half of what used to be "peca C". It does
NOT own the registry or the resolver (``step_skills.py``, owned by another
builder in this round) -- it consumes that module as a library, the same way
``workflow_v3.py`` already consumes siblings: by loading the sibling script
from its own file path, with no import-time package dependency. This module
never mutates ``step_skills.py``.

Hard constraints honoured: standard library only, no network, no dependency
on a real ``specify``/``node``/``backlogctl``. Every document (resolution,
dispatch intent, invocation envelopes, step output) arrives as a plain
argument; this module is pure data in / pure data out. The public CLI consumes
only :func:`judge_checkpoint_attestation` at a V3 completion boundary.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

# --------------------------------------------------------------------------
# sibling loader -- no import-time dependency on step_skills.py (mirrors
# workflow_v3.sibling()): this module must keep working whether it is loaded
# as part of the ``grill_core`` package or standalone via
# ``importlib.util.spec_from_file_location``, which is how the test suite
# loads sibling modules in this codebase today.
# --------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SIBLINGS: dict[str, Any] = {}


def _sibling(name: str) -> Any:
    cached = _SIBLINGS.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(f"grill_core._{name}", _SCRIPTS_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        raise _blocked("SIBLING_UNREADABLE", module=name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        # This lazy boundary runs inside the public checkpoint command.  Core
        # diagnostics must not get in front of that command's sole JSON line.
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    except BaseException as exc:
        sys.modules.pop(spec.name, None)
        raise _blocked("SIBLING_UNAVAILABLE", module=name, error=type(exc).__name__) from exc
    _SIBLINGS[name] = module
    return module


def _step_skills() -> Any:
    """The registry/resolver module (``step_skills.py``), loaded lazily."""
    return _sibling("step_skills")


# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

DISPATCH_INTENT_SCHEMA = "dispatch-intent/v1"
STEP_OUTPUT_SCHEMA = "step-output/v1"
CHECKPOINT_ATTESTATION_SCHEMA = "checkpoint-attestation/v1"

DISPATCH_STATUSES = ("RESERVED", "CALLING", "STARTED", "ABSENT", "UNKNOWN", "CANCELLED", "COMPLETED", "FAILED")
STEP_OUTPUT_RESULTS = ("COMPLETED", "FAILED", "BLOCKED", "UNKNOWN")
#: Terminal (non-STARTED) statuses a ``skill-invocation/v1`` may carry. Only
#: ``COMPLETED`` among these may back a ``step-output/v1`` (plan 4.1).
TERMINAL_INVOCATION_STATUSES = ("COMPLETED", "FAILED", "BLOCKED")

#: Fail-closed verdict codes. LD-002 revised: this is vocabulary the plan
#: names itself (4.1 / 22 / 23), so it is emitted verbatim in
#: SCREAMING_SNAKE -- never translated here. ``BLOCKED_CAPABILITY`` and
#: ``STALE_SKILL_RESOLUTION`` are the same v3 vocabulary ``step_skills.py``
#: already emits; this module reuses the literal strings (frozen, with a
#: cross-module drift test) rather than depending on the sibling being loaded
#: just to read a module-level constant.
BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"
STALE_SKILL_RESOLUTION = "STALE_SKILL_RESOLUTION"
UNATTESTED_STEP_OUTPUT = "UNATTESTED_STEP_OUTPUT"
#: New in this module: a receipt whose own hash checks out but whose
#: generation/plan revision is not the current one -- "replay de geracao ou
#: revisao anterior" (plan 22).
STALE_OUTPUT = "STALE_OUTPUT"
#: New in this module: a receipt that belongs to another step, skill, work
#: item, run, attempt or runtime, or bytes that diverge under a claimed-valid
#: hash (plan 22, bullet 7).
STATE_DIVERGENCE = "STATE_DIVERGENCE"
#: New in this module (plan bullet 5): the agent begins executing the step's
#: semantics directly -- declares a forbidden ``execution_mode``, or touches a
#: mutable capability before the canonical invocation reached ``STARTED``.
POLICY_VIOLATION = "POLICY_VIOLATION"
DIRECT_STEP_EXECUTION = "DIRECT_STEP_EXECUTION"
# A cryptographic-looking JSON transcript is not provenance.  The shipped
#: Event vocabulary, literal from plan section 7 ("Eventos e recuperacao").
EVENT_SKILL_RESOLVED = "workflow.skill.resolved"
EVENT_INVOCATION_STARTED = "workflow.skill.invocation.started"
EVENT_INVOCATION_COMPLETED = "workflow.skill.invocation.completed"
EVENT_INVOCATION_FAILED = "workflow.skill.invocation.failed"
EVENT_INVOCATION_BLOCKED = "workflow.skill.invocation.blocked"
EVENT_DIRECT_EXECUTION_REJECTED = "workflow.direct_execution.rejected"

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RECOVERY_GENERATION_ID_RE = re.compile(r"^rg-[0-9a-f]{64}$")
STEP_EXECUTION_ID_RE = re.compile(r"^se-[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FREE_REF_RE = re.compile(r"^[\x21-\x7e]([\x20-\x7e]{0,254})$")

#: ``dispatch-intent/v1``, exact keys, literal from plan 5.5.
_DISPATCH_INTENT_KEYS = (
    "schema", "dispatch_key", "project_id", "work_item_id", "run_id", "attempt_id",
    "step_id", "execution_mode", "skill_resolution_sha256", "skill_invocation_key",
    "logical_plan_sha256", "executable_plan_sha256", "recovery_generation_id",
    "plan_revision", "wave_index", "worktree_id", "worktree_head", "runtime", "adapter",
    "dispatch_payload_sha256", "dispatcher_epoch", "dispatcher_lease_id",
    "work_item_revision", "worker_lease_id", "worker_fencing_token", "status",
    "runtime_handle", "content_sha256",
)

#: The 14 fields the literal ``dispatch_key`` formula covers (plan 5.5, and
#: the task literal). Deliberately excludes ``attempt_id``, ``dispatcher_epoch``,
#: ``dispatcher_lease_id``, ``work_item_revision``, ``worker_lease_id``,
#: ``worker_fencing_token``, ``status``, ``runtime_handle`` and any timestamp
#: -- "A chave NAO inclui attempt, epoch, lease nem timestamp".
DISPATCH_KEY_FIELDS = (
    "project_id", "work_item_id", "run_id", "step_id", "recovery_generation_id",
    "plan_revision", "wave_index", "executable_plan_sha256", "skill_resolution_sha256",
    "worktree_id", "worktree_head", "runtime", "adapter", "dispatch_payload_sha256",
)

#: ``step-output/v1``, exact keys, literal from plan 7.1.3.
_STEP_OUTPUT_KEYS = (
    "schema", "recovery_generation_id", "plan_revision", "wave_index", "step_id",
    "skill_invocation_receipt_ref", "skill_invocation_receipt_sha256", "execution_round",
    "step_execution_id", "supersedes_step_execution_id", "attempt_id",
    "supersedes_attempt_id", "worker_lease_id", "worker_fencing_token",
    "input_fingerprint", "dependency_outputs", "output_sha256", "evidence_refs",
    "result", "content_sha256",
)
_DEPENDENCY_OUTPUT_KEYS = ("step_id", "output_sha256", "receipt_ref", "provenance")
_EVIDENCE_REF_KEYS = ("path", "sha256")
_PROVENANCE_VALUES = ("current-generation", "reused-clean")

#: Fields ``step_execution_id`` is derived from (plan 7.1.3, literal formula).
_STEP_EXECUTION_ID_FIELDS = (
    "recovery_generation_id", "plan_revision", "wave_index", "step_id",
    "execution_round", "input_fingerprint",
)

#: Fields that identify "the current campaign" a receipt must match to be
#: accepted as current rather than stale (used by ``judge_step_output``).
_EXPECTED_KEYS = (
    "project_id", "work_item_id", "run_id", "step_id", "runtime", "adapter",
    "registry_sha256", "recovery_generation_id", "plan_revision",
)
_CHECKPOINT_BUNDLE_REQUIRED_KEYS = (
    "schema", "resolution", "dispatch_intent", "invocation_started",
    "invocation_terminal", "step_output", "catalog",
)
_CHECKPOINT_CAMPAIGN_KEYS = (
    "project_id", "run_id", "runtime", "adapter", "registry_sha256",
    "recovery_generation_id", "plan_revision",
)
_HUMAN_AUTHORIZATION_KEYS = (
    "schema", "scope", "decision", "authorized_by", "receipt_ref", "content_sha256",
)


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------


class AttestationError(Exception):
    """Fail-closed outcome. ``code`` is one of ``BLOCKED_CAPABILITY``,
    ``STALE_SKILL_RESOLUTION``, ``UNATTESTED_STEP_OUTPUT``, ``STALE_OUTPUT``,
    ``STATE_DIVERGENCE`` or ``POLICY_VIOLATION``. ``event``, when set, is the
    plan-7 event name the caller must emit alongside the rejection (e.g.
    ``workflow.direct_execution.rejected``).
    """

    def __init__(self, code: str, reason: str, *, event: str | None = None, **detail: Any) -> None:
        super().__init__(f"{code}/{reason}")
        self.code = code
        self.reason = reason
        self.event = event
        self.detail = detail

    def payload(self) -> dict[str, Any]:
        out: dict[str, Any] = {"verdict": "REJECTED", "code": self.code, "reason": self.reason}
        if self.event:
            out["event"] = self.event
        if self.detail:
            out["detail"] = {k: self.detail[k] for k in sorted(self.detail)}
        return out


def _blocked(reason: str, **detail: Any) -> AttestationError:
    return AttestationError(BLOCKED_CAPABILITY, reason, **detail)


def _stale_resolution(reason: str, **detail: Any) -> AttestationError:
    return AttestationError(STALE_SKILL_RESOLUTION, reason, **detail)


def _unattested(reason: str, **detail: Any) -> AttestationError:
    return AttestationError(UNATTESTED_STEP_OUTPUT, reason, **detail)


def _stale_output(reason: str, **detail: Any) -> AttestationError:
    return AttestationError(STALE_OUTPUT, reason, **detail)


def _divergence(reason: str, **detail: Any) -> AttestationError:
    return AttestationError(STATE_DIVERGENCE, reason, **detail)


def _policy_violation(**detail: Any) -> AttestationError:
    return AttestationError(POLICY_VIOLATION, DIRECT_STEP_EXECUTION, event=EVENT_DIRECT_EXECUTION_REJECTED, **detail)


def reject_direct_execution(step_id: str, **detail: Any) -> AttestationError:
    """The section-22 adversarial fixture, verbatim: told to run a step, an
    agent executes the semantics directly (runs tests, writes a diff/report,
    merges/pushes/releases) and produces an artifact -- but the canonical
    skill was never resolved, dispatched or invoked. Zero receipts exist
    anywhere in the chain. Returns (does not raise) the error, matching the
    style of every other helper here -- the caller raises it.
    """
    return AttestationError(
        UNATTESTED_STEP_OUTPUT, "DIRECT_EXECUTION", event=EVENT_DIRECT_EXECUTION_REJECTED, step_id=step_id, **detail
    )


# --------------------------------------------------------------------------
# small validators (mirror step_skills.py's style; JCS/hash math is never
# reimplemented here -- always delegated to the sibling, per LD-001's lesson)
# --------------------------------------------------------------------------


def _require(condition: Any, reason: str, **detail: Any) -> None:
    if not condition:
        raise _blocked(reason, **detail)


def _exact_keys(value: Any, expected: Iterable[str], reason: str, **detail: Any) -> None:
    _require(isinstance(value, dict), reason, **detail, problem="not an object")
    got = set(value)
    want = set(expected)
    if got != want:
        raise _blocked(reason, **detail, missing=sorted(want - got), unexpected=sorted(got - want))


def _text(value: Any, pattern: re.Pattern[str], reason: str, **detail: Any) -> str:
    _require(isinstance(value, str) and bool(pattern.fullmatch(value)), reason, **detail, value=value)
    return value


def _nonneg_int(value: Any, reason: str, **detail: Any) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, reason, **detail, value=value)
    return value


def _assert_no_forbidden_fallback(document: Mapping[str, Any]) -> None:
    """Requirement 6: no ``DIRECT|EMULATED|BEST_EFFORT`` fallback anywhere in
    a serialized attestation structure for a ``required=true`` step (all 11
    registry steps are ``required=true`` -- see ``step_skills.validate_registry``).
    """
    ss = _step_skills()
    serialized = json.dumps(document)
    for mode in ss.FORBIDDEN_EXECUTION_MODES:
        if mode in serialized:
            raise _blocked("FORBIDDEN_EXECUTION_MODE", mode=mode)


# --------------------------------------------------------------------------
# dispatch-intent/v1 (plan 5.5)
# --------------------------------------------------------------------------


def dispatch_key(
    project_id: str,
    work_item_id: str,
    run_id: str,
    step_id: str,
    recovery_generation_id: str,
    plan_revision: int,
    wave_index: int,
    executable_plan_sha256: str,
    skill_resolution_sha256: str,
    worktree_id: str,
    worktree_head: str,
    runtime: str,
    adapter: str,
    dispatch_payload_sha256: str,
) -> str:
    """``dispatch_key = SHA256(JCS(project_id, work_item_id, run_id, step_id,
    recovery_generation_id, plan_revision, wave_index, executable_plan_sha256,
    skill_resolution_sha256, worktree_id, worktree_head, runtime, adapter,
    dispatch_payload_sha256))`` -- plan 5.5, literal.

    This signature has no ``attempt_id``, ``dispatcher_epoch``,
    ``dispatcher_lease_id``, ``worker_lease_id``, ``worker_fencing_token`` or
    timestamp parameter: the plan states the key excludes attempt/epoch/lease/
    timestamp, enforced here by the function simply not accepting them.
    """
    ss = _step_skills()
    fields = {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "run_id": run_id,
        "step_id": step_id,
        "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision,
        "wave_index": wave_index,
        "executable_plan_sha256": executable_plan_sha256,
        "skill_resolution_sha256": skill_resolution_sha256,
        "worktree_id": worktree_id,
        "worktree_head": worktree_head,
        "runtime": runtime,
        "adapter": adapter,
        "dispatch_payload_sha256": dispatch_payload_sha256,
    }
    return ss.sha256_jcs(fields)


def recompute_dispatch_key(document: Mapping[str, Any]) -> str:
    """Pull exactly the 14 canonical fields out of a full ``dispatch-intent/v1``
    document -- ignoring ``attempt_id``, ``dispatcher_epoch``,
    ``dispatcher_lease_id``, ``work_item_revision``, ``worker_lease_id``,
    ``worker_fencing_token``, ``status`` and ``runtime_handle`` -- and
    recompute the key. A full document whose attempt/epoch/lease fields were
    edited but whose declared ``dispatch_key`` was left alone must still
    recompute to the SAME key here: those fields are provably outside the
    digest domain, not merely undocumented.
    """
    return dispatch_key(*(document[field] for field in DISPATCH_KEY_FIELDS))


def validate_dispatch_intent(document: Any) -> dict[str, Any]:
    """Structural + identity validation of a ``dispatch-intent/v1`` envelope.
    Does not check correlation with a resolution/invocation/step -- that is
    ``_check_dispatch_binding``'s job, called from ``judge_step_output``.
    """
    ss = _step_skills()
    _exact_keys(document, _DISPATCH_INTENT_KEYS, "DISPATCH_INTENT_INVALID")
    _require(document["schema"] == DISPATCH_INTENT_SCHEMA, "DISPATCH_INTENT_SCHEMA", value=document["schema"])
    _require(document["status"] in DISPATCH_STATUSES, "DISPATCH_INTENT_STATUS", value=document["status"])
    _require(document["step_id"] in ss.SEQUENCE, "DISPATCH_INTENT_STEP", value=document["step_id"])
    _require(document["runtime"] in ss.RUNTIMES, "DISPATCH_INTENT_RUNTIME", value=document["runtime"])

    # execution_mode is checked before the generic forbidden-fallback scan:
    # a document that legitimately declares execution_mode="EMULATED" must be
    # caught as POLICY_VIOLATION/DIRECT_STEP_EXECUTION (a specific, named
    # policy breach), not swallowed by the generic BLOCKED_CAPABILITY scan
    # that only exists to catch the word turning up somewhere it has no
    # business being (an adapter id, a worktree ref, ...).
    mode = document["execution_mode"]
    if mode in ss.FORBIDDEN_EXECUTION_MODES:
        raise _policy_violation(step_id=document["step_id"], execution_mode=mode)
    _require(mode == ss.EXECUTION_MODE, "DISPATCH_INTENT_EXECUTION_MODE", value=mode)
    _assert_no_forbidden_fallback(document)

    for field in ("project_id", "work_item_id", "run_id", "worktree_id", "adapter", "dispatcher_lease_id",
                  "worker_lease_id", "attempt_id"):
        _text(document[field], FREE_REF_RE, "DISPATCH_INTENT_INVALID", field=field)
    _text(document["recovery_generation_id"], RECOVERY_GENERATION_ID_RE, "DISPATCH_INTENT_INVALID",
          field="recovery_generation_id")
    _text(document["worktree_head"], GIT_SHA_RE, "DISPATCH_INTENT_INVALID", field="worktree_head")
    for field in ("dispatch_key", "skill_resolution_sha256", "skill_invocation_key", "logical_plan_sha256",
                  "executable_plan_sha256", "dispatch_payload_sha256", "content_sha256"):
        _text(document[field], SHA256_RE, "INVALID_DIGEST", field=field)
    _nonneg_int(document["plan_revision"], "DISPATCH_INTENT_INVALID", field="plan_revision")
    _nonneg_int(document["wave_index"], "DISPATCH_INTENT_INVALID", field="wave_index")
    _nonneg_int(document["dispatcher_epoch"], "DISPATCH_INTENT_INVALID", field="dispatcher_epoch")
    _nonneg_int(document["work_item_revision"], "DISPATCH_INTENT_INVALID", field="work_item_revision")
    _nonneg_int(document["worker_fencing_token"], "DISPATCH_INTENT_INVALID", field="worker_fencing_token")
    _require(document["runtime_handle"] is None or isinstance(document["runtime_handle"], str),
              "DISPATCH_INTENT_INVALID", field="runtime_handle")

    body = {k: v for k, v in document.items() if k != "content_sha256"}
    if ss.sha256_jcs(body) != document["content_sha256"]:
        raise _divergence("DISPATCH_INTENT_CONTENT_MISMATCH")

    expected_key = recompute_dispatch_key(document)
    if expected_key != document["dispatch_key"]:
        raise _divergence("DISPATCH_KEY_MISMATCH", expected=expected_key, actual=document["dispatch_key"])

    return document


# --------------------------------------------------------------------------
# step-output/v1 (plan 7.1.3)
# --------------------------------------------------------------------------


def step_execution_id(
    recovery_generation_id: str, plan_revision: int, wave_index: int, step_id: str,
    execution_round: int, input_fingerprint: str,
) -> str:
    """``step_execution_id = SHA256(JCS(recovery_generation_id, plan_revision,
    wave_index, step_id, execution_round, input_fingerprint))`` -- plan
    7.1.3, literal, rendered as ``se-<hex>`` per the schema's own examples.
    """
    ss = _step_skills()
    fields = {
        "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision,
        "wave_index": wave_index,
        "step_id": step_id,
        "execution_round": execution_round,
        "input_fingerprint": input_fingerprint,
    }
    return "se-" + ss.sha256_jcs(fields).split(":", 1)[1]


def _validate_dependency_outputs(value: Any) -> None:
    ss = _step_skills()
    _require(isinstance(value, list), "STEP_OUTPUT_DEPENDENCY_OUTPUTS", problem="not a list")
    for index, item in enumerate(value):
        _exact_keys(item, _DEPENDENCY_OUTPUT_KEYS, "STEP_OUTPUT_DEPENDENCY_OUTPUT_INVALID", index=index)
        _require(item["step_id"] in ss.SEQUENCE, "STEP_OUTPUT_DEPENDENCY_OUTPUT_INVALID", index=index, field="step_id")
        _text(item["output_sha256"], SHA256_RE, "INVALID_DIGEST", index=index, field="output_sha256")
        _text(item["receipt_ref"], FREE_REF_RE, "STEP_OUTPUT_DEPENDENCY_OUTPUT_INVALID", index=index, field="receipt_ref")
        _require(item["provenance"] in _PROVENANCE_VALUES, "STEP_OUTPUT_DEPENDENCY_OUTPUT_INVALID",
                  index=index, field="provenance")


def _validate_evidence_refs(value: Any) -> None:
    _require(isinstance(value, list), "STEP_OUTPUT_EVIDENCE_REFS", problem="not a list")
    for index, item in enumerate(value):
        _exact_keys(item, _EVIDENCE_REF_KEYS, "STEP_OUTPUT_EVIDENCE_REF_INVALID", index=index)
        _text(item["path"], FREE_REF_RE, "STEP_OUTPUT_EVIDENCE_REF_INVALID", index=index, field="path")
        _text(item["sha256"], SHA256_RE, "INVALID_DIGEST", index=index, field="sha256")


def validate_step_output(document: Any) -> dict[str, Any]:
    """Structural + self-consistency validation of a ``step-output/v1``
    receipt. Does not check correlation with an invocation terminal or the
    current campaign -- that is ``_check_output_binding``'s job, called from
    ``judge_step_output``.
    """
    ss = _step_skills()
    _exact_keys(document, _STEP_OUTPUT_KEYS, "STEP_OUTPUT_INVALID")
    _require(document["schema"] == STEP_OUTPUT_SCHEMA, "STEP_OUTPUT_SCHEMA", value=document["schema"])
    _require(document["step_id"] in ss.SEQUENCE, "STEP_OUTPUT_STEP", value=document["step_id"])
    _require(document["result"] in STEP_OUTPUT_RESULTS, "STEP_OUTPUT_RESULT", value=document["result"])
    _assert_no_forbidden_fallback(document)

    _text(document["recovery_generation_id"], RECOVERY_GENERATION_ID_RE, "STEP_OUTPUT_INVALID",
          field="recovery_generation_id")
    _text(document["step_execution_id"], STEP_EXECUTION_ID_RE, "STEP_OUTPUT_INVALID", field="step_execution_id")
    if document["supersedes_step_execution_id"] is not None:
        _text(document["supersedes_step_execution_id"], STEP_EXECUTION_ID_RE, "STEP_OUTPUT_INVALID",
              field="supersedes_step_execution_id")
    if document["supersedes_attempt_id"] is not None:
        _text(document["supersedes_attempt_id"], FREE_REF_RE, "STEP_OUTPUT_INVALID", field="supersedes_attempt_id")
    for field in ("attempt_id", "worker_lease_id", "skill_invocation_receipt_ref"):
        _text(document[field], FREE_REF_RE, "STEP_OUTPUT_INVALID", field=field)
    for field in ("skill_invocation_receipt_sha256", "input_fingerprint", "output_sha256", "content_sha256"):
        _text(document[field], SHA256_RE, "INVALID_DIGEST", field=field)
    _nonneg_int(document["plan_revision"], "STEP_OUTPUT_INVALID", field="plan_revision")
    _nonneg_int(document["wave_index"], "STEP_OUTPUT_INVALID", field="wave_index")
    _require(isinstance(document["execution_round"], int) and not isinstance(document["execution_round"], bool)
              and document["execution_round"] >= 1, "STEP_OUTPUT_INVALID", field="execution_round")
    _nonneg_int(document["worker_fencing_token"], "STEP_OUTPUT_INVALID", field="worker_fencing_token")
    _validate_dependency_outputs(document["dependency_outputs"])
    _validate_evidence_refs(document["evidence_refs"])

    expected_exec_id = step_execution_id(*(document[f] for f in _STEP_EXECUTION_ID_FIELDS))
    if expected_exec_id != document["step_execution_id"]:
        raise _divergence("STEP_EXECUTION_ID_MISMATCH", expected=expected_exec_id, actual=document["step_execution_id"])

    body = {k: v for k, v in document.items() if k != "content_sha256"}
    if ss.sha256_jcs(body) != document["content_sha256"]:
        raise _divergence("STEP_OUTPUT_CONTENT_MISMATCH")

    return document


def receipt_sha256(document: Mapping[str, Any]) -> str:
    """Hash of a receipt exactly as stored (the whole document, including its
    own ``content_sha256`` field) -- what ``step-output/v1
    .skill_invocation_receipt_sha256`` binds to. Distinct from a document's
    self-hash (``content_sha256``, computed over the body *without* that
    field): this is the hash of the receipt file as a whole, the same
    quantity an honest step-output author would get from hashing the actual
    receipt bytes on disk.
    """
    ss = _step_skills()
    return ss.sha256_jcs(document)


# --------------------------------------------------------------------------
# capability guard (plan 4.1 / bullet 5)
# --------------------------------------------------------------------------


def guard_capability_access(invocation_started: Mapping[str, Any] | None, *, capability: str, step_id: str) -> None:
    """Plan 4.1: "capabilities de dominio permanecem bloqueadas ate o receipt
    skill-invocation STARTED". Call this before granting any mutable
    capability (git write, filesystem write outside the sandbox, network,
    merge/push/release, ...) to a step's execution. No STARTED receipt for
    the canonical invocation -> the agent is about to execute the semantics
    directly -> ``POLICY_VIOLATION/DIRECT_STEP_EXECUTION``, capability fenced.
    """
    if invocation_started is None or invocation_started.get("status") != "STARTED":
        raise _policy_violation(step_id=step_id, capability=capability)


# --------------------------------------------------------------------------
# the chain judge (plan 4.1)
# --------------------------------------------------------------------------


def _check_resolution(resolution: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    ss = _step_skills()
    if not isinstance(resolution, Mapping) or resolution.get("schema") != ss.RESOLUTION_SCHEMA:
        raise _unattested("RESOLUTION_INVALID")
    if resolution.get("step_id") != expected["step_id"] or resolution.get("runtime") != expected["runtime"]:
        raise _divergence(
            "RESOLUTION_IDENTITY_MISMATCH",
            expected={"step_id": expected["step_id"], "runtime": expected["runtime"]},
            actual={"step_id": resolution.get("step_id"), "runtime": resolution.get("runtime")},
        )
    if resolution.get("registry_sha256") != expected["registry_sha256"]:
        raise _stale_resolution(
            "REGISTRY_SHA256_MISMATCH", expected=expected["registry_sha256"], actual=resolution.get("registry_sha256")
        )
    mode = resolution.get("execution_mode")
    if mode in ss.FORBIDDEN_EXECUTION_MODES:
        raise _policy_violation(step_id=expected["step_id"], execution_mode=mode)
    _require(mode == ss.EXECUTION_MODE, "RESOLUTION_EXECUTION_MODE", value=mode)
    if not ss.verify_resolution_digest(resolution):
        raise _divergence("RESOLUTION_CONTENT_MISMATCH")


def _check_dispatch_binding(
    dispatch_intent: Mapping[str, Any], resolution: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    for field in ("project_id", "work_item_id", "run_id", "step_id", "runtime", "adapter"):
        if dispatch_intent[field] != expected[field]:
            raise _divergence("DISPATCH_IDENTITY_MISMATCH", field=field, expected=expected[field], actual=dispatch_intent[field])
    if dispatch_intent["skill_resolution_sha256"] != resolution["skill_resolution_sha256"]:
        raise _divergence(
            "DISPATCH_RESOLUTION_MISMATCH",
            expected=resolution["skill_resolution_sha256"],
            actual=dispatch_intent["skill_resolution_sha256"],
        )
    current = (expected["recovery_generation_id"], expected["plan_revision"])
    seen = (dispatch_intent["recovery_generation_id"], dispatch_intent["plan_revision"])
    if seen != current:
        raise _stale_output(
            "DISPATCH_GENERATION_STALE",
            expected={"recovery_generation_id": current[0], "plan_revision": current[1]},
            actual={"recovery_generation_id": seen[0], "plan_revision": seen[1]},
        )


def _check_invocation_binding(
    invocation: Mapping[str, Any], dispatch_intent: Mapping[str, Any], expected: Mapping[str, Any], expected_status: str
) -> None:
    if invocation["status"] != expected_status:
        raise _unattested("INVOCATION_STATUS_UNEXPECTED", expected=expected_status, actual=invocation["status"])
    for field in ("project_id", "work_item_id", "run_id", "step_id"):
        if invocation[field] != expected[field]:
            raise _divergence("INVOCATION_IDENTITY_MISMATCH", field=field, expected=expected[field], actual=invocation[field])
    if invocation["dispatch_key"] != dispatch_intent["dispatch_key"]:
        raise _divergence(
            "INVOCATION_DISPATCH_MISMATCH", expected=dispatch_intent["dispatch_key"], actual=invocation["dispatch_key"]
        )
    if invocation["skill_invocation_key"] != dispatch_intent["skill_invocation_key"]:
        raise _divergence(
            "INVOCATION_KEY_DISPATCH_MISMATCH",
            expected=dispatch_intent["skill_invocation_key"],
            actual=invocation["skill_invocation_key"],
        )


def _check_output_binding(
    step_output: Mapping[str, Any], invocation_terminal: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """The four-way taxonomy of plan 22, bullet 7, applied to the final link:

    * no correlated receipt              -> ``UNATTESTED_STEP_OUTPUT``
    * receipt of another step            -> ``STATE_DIVERGENCE``
    * replay of an earlier generation    -> ``STALE_OUTPUT``
    * bytes divergent under a claimed-valid hash -> caught upstream by
      ``validate_step_output``'s own ``content_sha256`` recheck, also
      ``STATE_DIVERGENCE``.
    """
    if step_output["step_id"] != expected["step_id"]:
        raise _divergence("STEP_OUTPUT_STEP_MISMATCH", expected=expected["step_id"], actual=step_output["step_id"])
    if step_output["skill_invocation_receipt_sha256"] != receipt_sha256(invocation_terminal):
        raise _unattested("RECEIPT_NOT_CORRELATED")
    current = (expected["recovery_generation_id"], expected["plan_revision"])
    seen = (step_output["recovery_generation_id"], step_output["plan_revision"])
    if seen != current:
        raise _stale_output(
            "STEP_OUTPUT_GENERATION_STALE",
            expected={"recovery_generation_id": current[0], "plan_revision": current[1]},
            actual={"recovery_generation_id": seen[0], "plan_revision": seen[1]},
        )
    if step_output["result"] != "COMPLETED":
        raise _unattested("STEP_OUTPUT_NOT_COMPLETED", value=step_output["result"])


def judge_step_output(
    *,
    step_output: Mapping[str, Any] | None,
    dispatch_intent: Mapping[str, Any] | None,
    invocation_started: Mapping[str, Any] | None,
    invocation_terminal: Mapping[str, Any] | None,
    resolution: Mapping[str, Any] | None,
    expected: Mapping[str, Any],
    catalog: Mapping[str, Any],
    human_authorization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Judge the full chain of plan 4.1: ``resolution -> dispatch-intent
    CANONICAL_SKILL -> invocation STARTED -> invocation COMPLETED ->
    step-output``, in that order. Returns an ``ATTESTED`` verdict only if
    every link is present, self-consistent and correlated; otherwise raises
    ``AttestationError``.

    ``expected`` pins the current campaign: ``project_id``, ``work_item_id``,
    ``run_id``, ``step_id``, ``runtime``, ``adapter``, ``registry_sha256``,
    ``recovery_generation_id`` and ``plan_revision`` -- see ``_EXPECTED_KEYS``.

    ``catalog`` is the observed runtime capability catalogue needed to anchor
    both invocation receipts back to the canonical resolution.  It is not a
    trust declaration: ``validate_skill_invocation`` resolves it against the
    versioned trusted-catalog asset on disk, so a caller cannot authorize a
    tampered in-memory catalogue merely by handing it to this function.

    ``human_authorization`` is accepted but never inspected by this function.
    That is deliberate, not an oversight: plan 4.1 says authorization to run
    ``ship`` "permite invocar a skill ship, mas nunca substitui a skill nem
    autoriza side effects diretos" -- a valid human authorization changes
    nothing about whether the chain is attested. Its only legitimate effect
    is upstream, on whether the canonical ``ship`` skill was allowed to be
    dispatched in the first place.
    """
    _require(set(expected) >= set(_EXPECTED_KEYS), "EXPECTED_INVALID", missing=sorted(set(_EXPECTED_KEYS) - set(expected)))
    step_id = expected["step_id"]

    if resolution is None and dispatch_intent is None and invocation_started is None and invocation_terminal is None:
        raise reject_direct_execution(step_id)

    if resolution is None:
        raise _unattested("RESOLUTION_MISSING", step_id=step_id)
    _check_resolution(resolution, expected)

    if dispatch_intent is None:
        raise _unattested("DISPATCH_INTENT_MISSING", step_id=step_id)
    validate_dispatch_intent(dispatch_intent)
    _check_dispatch_binding(dispatch_intent, resolution, expected)

    ss = _step_skills()
    invocation_context = {
        "project_id": expected["project_id"],
        "work_item_id": expected["work_item_id"],
        "run_id": expected["run_id"],
        "attempt_id": dispatch_intent["attempt_id"],
        "catalog": catalog,
    }

    if invocation_started is None:
        raise _unattested("INVOCATION_STARTED_MISSING", step_id=step_id)
    ss.validate_skill_invocation(invocation_started, resolution, **invocation_context)
    _check_invocation_binding(invocation_started, dispatch_intent, expected, "STARTED")

    if invocation_terminal is None:
        raise _unattested("INVOCATION_TERMINAL_MISSING", step_id=step_id)
    ss.validate_skill_invocation(invocation_terminal, resolution, **invocation_context)
    _require(invocation_terminal["status"] in TERMINAL_INVOCATION_STATUSES,
              "INVOCATION_TERMINAL_STATUS", value=invocation_terminal["status"])
    if invocation_terminal["skill_invocation_key"] != invocation_started["skill_invocation_key"]:
        raise _divergence(
            "INVOCATION_TERMINAL_IDENTITY_MISMATCH",
            expected=invocation_started["skill_invocation_key"],
            actual=invocation_terminal["skill_invocation_key"],
        )
    if invocation_terminal["status"] != "COMPLETED":
        raise _unattested("INVOCATION_NOT_COMPLETED", status=invocation_terminal["status"])

    if step_output is None:
        raise _unattested("STEP_OUTPUT_MISSING", step_id=step_id)
    validate_step_output(step_output)
    _check_output_binding(step_output, invocation_terminal, expected)

    return {
        "verdict": "ATTESTED",
        "step_id": step_id,
        "step_execution_id": step_output["step_execution_id"],
        "skill_invocation_key": invocation_terminal["skill_invocation_key"],
    }


def _checkpoint_campaign(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the campaign fields that bind all checkpoints in one run."""
    _exact_keys(value, _CHECKPOINT_CAMPAIGN_KEYS, "CHECKPOINT_CAMPAIGN_INVALID")
    _text(value["project_id"], SHA256_RE, "CHECKPOINT_CAMPAIGN_INVALID", field="project_id")
    _text(value["run_id"], FREE_REF_RE, "CHECKPOINT_CAMPAIGN_INVALID", field="run_id")
    _require(value["runtime"] in _step_skills().RUNTIMES, "CHECKPOINT_CAMPAIGN_INVALID", field="runtime")
    _text(value["adapter"], FREE_REF_RE, "CHECKPOINT_CAMPAIGN_INVALID", field="adapter")
    _text(value["registry_sha256"], SHA256_RE, "CHECKPOINT_CAMPAIGN_INVALID", field="registry_sha256")
    _text(value["recovery_generation_id"], RECOVERY_GENERATION_ID_RE,
          "CHECKPOINT_CAMPAIGN_INVALID", field="recovery_generation_id")
    _nonneg_int(value["plan_revision"], "CHECKPOINT_CAMPAIGN_INVALID", field="plan_revision")
    return dict(value)


def _validate_human_authorization(value: Any, step_id: str) -> Mapping[str, Any]:
    _exact_keys(value, _HUMAN_AUTHORIZATION_KEYS, "HUMAN_AUTHORIZATION_INVALID")
    _require(value["schema"] == "human-authorization/v1", "HUMAN_AUTHORIZATION_INVALID", field="schema")
    _require(value["scope"] == step_id, "HUMAN_AUTHORIZATION_SCOPE", expected=step_id, actual=value["scope"])
    _require(value["decision"] == "APPROVED", "HUMAN_AUTHORIZATION_NOT_APPROVED")
    for field in ("authorized_by", "receipt_ref"):
        _text(value[field], FREE_REF_RE, "HUMAN_AUTHORIZATION_INVALID", field=field)
    _text(value["content_sha256"], SHA256_RE, "HUMAN_AUTHORIZATION_INVALID", field="content_sha256")
    return value



# ---------------------------------------------------------------------------
# Emission
#
# The core has always known how to *judge* a chain and never how to *mint* one,
# so every step of the cycle was unreachable by checkpoint once the gate that
# demands a chain started firing.  Closing that gap is what this section does.
#
# What it mints is exactly what specs/010 scoped: structural correlation.  A
# receipt minted here proves an artefact existed and was read at emission time,
# and that altering it afterwards breaks the correlation.  It does not prove the
# registered skill ran.  Saying otherwise in a docstring would be the same
# over-claim the whole mechanism exists to prevent.
# ---------------------------------------------------------------------------


class EmissionError(AttestationError):
    """A chain could not be minted from truthful inputs.

    Deliberately a subclass: a caller that already handles ``AttestationError``
    keeps failing closed on emission problems rather than letting one through
    as an unrelated exception type.
    """


#: Emission refusals are their own code. They are not ``BLOCKED_CAPABILITY``
#: (the capability may be perfectly resolvable) nor ``UNATTESTED_STEP_OUTPUT``
#: (nothing was attested -- minting is what failed).
EMISSION_REFUSED = "EMISSION_REFUSED"


def _emit_fail(reason: str, **detail: Any) -> EmissionError:
    return EmissionError(EMISSION_REFUSED, reason, **detail)


def execution_class(step_id: str, workflow_version: str, versions: Any) -> str:
    """Return ``leader-allowed`` or ``worker-required`` for one step.

    A step absent from the table fails closed naming the missing decision: a
    step added to a sequence without a class here must not inherit a permissive
    default from its neighbour (ADR-0203).
    """
    table = versions.EXECUTION_CLASS_BY_VERSION.get(workflow_version)
    if table is None:
        raise _emit_fail("EXECUTION_CLASS_VERSION_UNKNOWN", workflow_version=workflow_version)
    klass = table.get(step_id)
    if klass is None:
        raise _emit_fail("EXECUTION_CLASS_UNDECLARED", step_id=step_id, workflow_version=workflow_version)
    if klass not in versions.EXECUTION_CLASSES:
        raise _emit_fail("EXECUTION_CLASS_INVALID", step_id=step_id, value=klass)
    return klass


def require_emission_allowed(
    step_id: str,
    workflow_version: str,
    versions: Any,
    *,
    worker_execution_proven: bool = False,
) -> str:
    """Decide whether a chain may be minted for this step, and say why not.

    ``worker-required`` never meant "the worker writes the receipt" -- no worker
    ever writes a step receipt. ``implement-parallel`` is explicit that the step
    receipt belongs to the leader and that no worker checkpoints a step. What
    the class means is that the *work* must have been done by dispatched
    workers, because their worktree isolation and closed file grant are the
    step's safety mechanism.

    So the leader may mint for such a step, but only against proof that workers
    actually ran: converged waves covering the DAG. Without that proof the
    receipt would attest an isolation that never happened, which is worse than
    no receipt at all. With it, refusing would strand the one step that did use
    workers -- which is exactly what the earlier unconditional refusal did.

    Returns the class, so a caller can record which rule it satisfied.
    """
    klass = execution_class(step_id, workflow_version, versions)
    if klass == "worker-required" and not worker_execution_proven:
        raise _emit_fail(
            "WORKER_EXECUTION_UNPROVEN",
            step_id=step_id,
            workflow_version=workflow_version,
            needed="converged waves covering the execution DAG",
        )
    return klass


def artefact_digest(read_bytes: Callable[[str], bytes], path: str) -> tuple[str, int]:
    """Read the declared artefact and return ``(digest, size)``.

    ``read_bytes`` is the caller's already-safe boundary -- the CLI passes the
    no-follow descriptor reader it uses everywhere else, so this module keeps
    doing no I/O of its own.  An unreadable or absent artefact is a named
    refusal; it is never a chain minted with an empty digest (ADR-0202).
    """
    if not isinstance(path, str) or not path.strip():
        raise _emit_fail("ARTEFACT_PATH_INVALID", path=path)
    try:
        raw = read_bytes(path)
    except Exception as exc:  # the caller's boundary decides what is unsafe
        raise _emit_fail("ARTEFACT_UNREADABLE", path=path, error=type(exc).__name__) from exc
    if not isinstance(raw, (bytes, bytearray)):
        raise _emit_fail("ARTEFACT_UNREADABLE", path=path, problem="reader returned non-bytes")
    return "sha256:" + hashlib.sha256(bytes(raw)).hexdigest(), len(raw)


#: Which terminal invocation status accompanies each step result. The two
#: vocabularies overlap on the three terminal values but are not the same set:
#: ``STEP_OUTPUT_RESULTS`` also admits ``UNKNOWN``, which no invocation status
#: matches. Kept as an explicit map rather than passing the result straight
#: through, so that a result with no counterpart refuses instead of minting an
#: invocation whose status is not a status.
_INVOCATION_STATUS_FOR_RESULT = {
    "COMPLETED": "COMPLETED",
    "FAILED": "FAILED",
    "BLOCKED": "BLOCKED",
}



def leader_lease(run_id: str, step_id: str) -> tuple[str, int]:
    """Derive the conducting session's lease for one step.

    Mirrors how a worker lease is minted in ``gauntlet_runs``: the identifier is
    derived from the run plus the executor's identity, and the fencing token
    starts at one.  There is no global counter to consult, and inventing one
    here would be a second source of truth for the same thing.

    Uniqueness therefore comes from the pair. Two leader executions of the same
    step in the same run are the same logical executor -- exactly as two workers
    with the same node id in the same run would be -- so they share a lease by
    construction rather than by accident.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise _emit_fail("LEASE_RUN_INVALID", run_id=run_id)
    if not isinstance(step_id, str) or not step_id.strip():
        raise _emit_fail("LEASE_STEP_INVALID", step_id=step_id)
    return f"lease-{run_id}-leader-{step_id}", 1

def mint_chain(
    *,
    resolution: Mapping[str, Any],
    project_id: str,
    work_item_id: str,
    work_item_revision: int,
    run_id: str,
    step_id: str,
    attempt_id: str,
    recovery_generation_id: str,
    plan_revision: int,
    wave_index: int,
    worktree_id: str,
    worktree_head: str,
    worker_lease_id: str,
    worker_fencing_token: int,
    dispatcher_lease_id: str,
    dispatcher_epoch: int,
    artefact_path: str,
    artefact_sha256: str,
    logical_plan_sha256: str,
    executable_plan_sha256: str,
    input_fingerprint: str,
    dependency_outputs: Iterable[Mapping[str, Any]] = (),
    execution_round: int = 1,
    result: str = "COMPLETED",
    catalog: Mapping[str, Any] | None = None,
    supersedes_step_execution_id: str | None = None,
    supersedes_attempt_id: str | None = None,
) -> dict[str, Any]:
    """Mint the four correlated links plus the catalog, ready for the checkpoint.

    Every caller-supplied value must already be true of the world: the digests
    are computed here, but what they are computed *over* is the caller's
    responsibility.  ``artefact_sha256`` in particular is expected to come from
    :func:`artefact_digest`, which reads the file through the caller's safe
    boundary -- this function does no I/O and cannot verify that the artefact
    exists.

    What the returned chain proves is what specs/010 scoped: correlation. It
    says an artefact with this digest was named for this step, under this
    resolution of the registered skill. It does not say the skill ran.
    """
    ss = _step_skills()
    if not isinstance(resolution, Mapping):
        raise _emit_fail("RESOLUTION_INVALID", problem="not an object")
    for field in ("skill_resolution_sha256", "adapter", "runtime", "skill_id",
                  "skill_version", "skill_content_sha256", "registry_sha256", "entrypoint"):
        if field not in resolution:
            raise _emit_fail("RESOLUTION_INCOMPLETE", field=field)
    _text(artefact_sha256, SHA256_RE, "INVALID_DIGEST", field="artefact_sha256")

    # The two back-references travel together or not at all. One without the
    # other names half of what it replaces, which is worse than naming nothing:
    # an auditor would see a supersession and be unable to resolve it.
    supersedes = (supersedes_step_execution_id, supersedes_attempt_id)
    if any(value is not None for value in supersedes):
        if any(value is None for value in supersedes):
            raise _emit_fail(
                "SUPERSEDE_LINK_INCOMPLETE",
                supersedes_step_execution_id=supersedes_step_execution_id,
                supersedes_attempt_id=supersedes_attempt_id,
            )
        _text(supersedes_step_execution_id, STEP_EXECUTION_ID_RE,
              "SUPERSEDE_LINK_INVALID", field="supersedes_step_execution_id")
        # Round one is by definition the first: a receipt that claims to replace
        # something while being the first attempt is minting its own history.
        if execution_round <= 1:
            raise _emit_fail("SUPERSEDE_ROUND_NOT_ADVANCED", execution_round=execution_round)

    runtime = resolution["runtime"]
    adapter = resolution["adapter"]
    resolution_sha = resolution["skill_resolution_sha256"]

    # The dispatch payload of a leader-executed step is the declaration itself:
    # who executes what, where, anchored on which artefact.  Hashing that is
    # truthful; inventing a payload digest would not be.
    dispatch_payload_sha256 = ss.sha256_jcs({
        "step_id": step_id,
        "artefact_path": artefact_path,
        "artefact_sha256": artefact_sha256,
        "worktree_id": worktree_id,
        "worktree_head": worktree_head,
        "worker_lease_id": worker_lease_id,
    })

    dkey = dispatch_key(
        project_id, work_item_id, run_id, step_id, recovery_generation_id, plan_revision,
        wave_index, executable_plan_sha256, resolution_sha, worktree_id, worktree_head,
        runtime, adapter, dispatch_payload_sha256,
    )
    ikey = ss.skill_invocation_key(
        project_id, work_item_id, run_id, step_id, recovery_generation_id, plan_revision,
        resolution_sha, dkey,
    )

    dispatch_body: dict[str, Any] = {
        "schema": DISPATCH_INTENT_SCHEMA,
        "dispatch_key": dkey,
        "project_id": project_id,
        "work_item_id": work_item_id,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "step_id": step_id,
        "execution_mode": ss.EXECUTION_MODE,
        "skill_resolution_sha256": resolution_sha,
        "skill_invocation_key": ikey,
        "logical_plan_sha256": logical_plan_sha256,
        "executable_plan_sha256": executable_plan_sha256,
        "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision,
        "wave_index": wave_index,
        "worktree_id": worktree_id,
        "worktree_head": worktree_head,
        "runtime": runtime,
        "adapter": adapter,
        "dispatch_payload_sha256": dispatch_payload_sha256,
        "dispatcher_epoch": dispatcher_epoch,
        "dispatcher_lease_id": dispatcher_lease_id,
        "work_item_revision": work_item_revision,
        "worker_lease_id": worker_lease_id,
        "worker_fencing_token": worker_fencing_token,
        "status": "STARTED",
        "runtime_handle": None,
    }
    dispatch_body["content_sha256"] = ss.sha256_jcs(dispatch_body)

    def _invocation(status: str, output_manifest_sha256: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": ss.INVOCATION_SCHEMA,
            "skill_invocation_key": ikey,
            "project_id": project_id,
            "work_item_id": work_item_id,
            "run_id": run_id,
            "step_id": step_id,
            "skill_id": resolution["skill_id"],
            "skill_version": resolution["skill_version"],
            "skill_content_sha256": resolution["skill_content_sha256"],
            "registry_sha256": resolution["registry_sha256"],
            "skill_resolution_sha256": resolution_sha,
            "runtime": runtime,
            "adapter": adapter,
            "entrypoint": resolution["entrypoint"],
            "dispatch_key": dkey,
            "attempt_id": attempt_id,
            "recovery_generation_id": recovery_generation_id,
            "plan_revision": plan_revision,
            "input_fingerprint": input_fingerprint,
            "started_receipt_ref": f"receipts/skill-invocation/{step_id}-{attempt_id}.started.json",
            "status": status,
            "output_manifest_sha256": output_manifest_sha256,
        }
        body["content_sha256"] = ss.sha256_jcs(body)
        return body

    # STARTED has no output yet; its manifest digest is over the empty manifest,
    # not over a placeholder string. The terminal one is over the real artefact.
    # Two vocabularies, deliberately not merged: an invocation reports whether
    # the call finished, a step output whether the step achieved its result.
    # They overlap on three terminal values and diverge on a fourth -- a step
    # output may be UNKNOWN, which no invocation status matches. Collapsing
    # them would let a completed call that produced a failed step read as
    # success.
    invocation_status = _INVOCATION_STATUS_FOR_RESULT.get(result)
    if invocation_status is None:
        raise _emit_fail("STEP_RESULT_UNKNOWN", result=result)
    invocation_started = _invocation("STARTED", ss.sha256_jcs([]))
    invocation_terminal = _invocation(invocation_status, ss.sha256_jcs([
        {"path": artefact_path, "sha256": artefact_sha256},
    ]))

    exec_id = step_execution_id(
        recovery_generation_id, plan_revision, wave_index, step_id, execution_round, input_fingerprint,
    )
    step_output_body: dict[str, Any] = {
        "schema": STEP_OUTPUT_SCHEMA,
        "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision,
        "wave_index": wave_index,
        "step_id": step_id,
        "skill_invocation_receipt_ref": f"receipts/skill-invocation/{step_id}-{attempt_id}.terminal.json",
        "skill_invocation_receipt_sha256": receipt_sha256(invocation_terminal),
        "execution_round": execution_round,
        "step_execution_id": exec_id,
        "supersedes_step_execution_id": supersedes_step_execution_id,
        "attempt_id": attempt_id,
        "supersedes_attempt_id": supersedes_attempt_id,
        "worker_lease_id": worker_lease_id,
        "worker_fencing_token": worker_fencing_token,
        "input_fingerprint": input_fingerprint,
        "dependency_outputs": [dict(item) for item in dependency_outputs],
        # The artefact digest IS the step output digest. There is no second,
        # separate notion of "the output" to hash -- that is the whole point of
        # anchoring on a declared artefact (ADR-0202).
        "output_sha256": artefact_sha256,
        "evidence_refs": [{"path": artefact_path, "sha256": artefact_sha256}],
        "result": result,
    }
    step_output_body["content_sha256"] = ss.sha256_jcs(step_output_body)

    bundle: dict[str, Any] = {
        "schema": CHECKPOINT_ATTESTATION_SCHEMA,
        "resolution": dict(resolution),
        "dispatch_intent": dispatch_body,
        "invocation_started": invocation_started,
        "invocation_terminal": invocation_terminal,
        "step_output": step_output_body,
        "catalog": dict(catalog) if catalog is not None else resolution.get("catalog"),
    }
    return bundle

def judge_checkpoint_attestation(
    bundle: Mapping[str, Any],
    *,
    project_id: str,
    work_item_id: str,
    step_id: str,
    campaign: Mapping[str, Any] | None = None,
    predecessor_output: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the only receipt form that may complete a v3 checkpoint.

    The public CLI supplies the project/work-item/step context from its own
    state, never from the receipt.  The first accepted step establishes a
    seven-field campaign; every later step must match it and carry exactly the
    recorded direct predecessor output.  Thus a valid receipt for ``ship``
    cannot be replayed into a fresh item or skip the immutable external order.
    """
    _require(isinstance(bundle, Mapping), "CHECKPOINT_ATTESTATION_INVALID", problem="not an object")
    expected_keys = set(_CHECKPOINT_BUNDLE_REQUIRED_KEYS)
    if "human_authorization" in bundle:
        expected_keys.add("human_authorization")
    _require(set(bundle) == expected_keys, "CHECKPOINT_ATTESTATION_INVALID",
             missing=sorted(expected_keys - set(bundle)), unexpected=sorted(set(bundle) - expected_keys))
    _require(bundle["schema"] == CHECKPOINT_ATTESTATION_SCHEMA,
             "CHECKPOINT_ATTESTATION_SCHEMA", value=bundle["schema"])
    resolution = bundle["resolution"]
    dispatch = bundle["dispatch_intent"]
    _require(isinstance(resolution, Mapping) and isinstance(dispatch, Mapping),
             "CHECKPOINT_ATTESTATION_INVALID", problem="resolution or dispatch invalid")
    observed = _checkpoint_campaign({
        "project_id": project_id,
        "run_id": dispatch.get("run_id"),
        "runtime": resolution.get("runtime"),
        "adapter": resolution.get("adapter"),
        "registry_sha256": resolution.get("registry_sha256"),
        "recovery_generation_id": dispatch.get("recovery_generation_id"),
        "plan_revision": dispatch.get("plan_revision"),
    })
    if campaign is not None and _checkpoint_campaign(campaign) != observed:
        raise _stale_output("CHECKPOINT_CAMPAIGN_STALE", expected=dict(campaign), actual=observed)
    expected = {**observed, "work_item_id": work_item_id, "step_id": step_id}
    authorization = bundle.get("human_authorization")
    if resolution.get("human_authorization_required"):
        if authorization is None:
            raise _unattested("HUMAN_AUTHORIZATION_MISSING", step_id=step_id)
        _validate_human_authorization(authorization, step_id)
    elif authorization is not None:
        _validate_human_authorization(authorization, step_id)
    verdict = judge_step_output(
        step_output=bundle["step_output"],
        dispatch_intent=dispatch,
        invocation_started=bundle["invocation_started"],
        invocation_terminal=bundle["invocation_terminal"],
        resolution=resolution,
        expected=expected,
        catalog=bundle["catalog"],
        human_authorization=authorization,
    )
    step_output = bundle["step_output"]
    expected_dependencies = [] if predecessor_output is None else [dict(predecessor_output)]
    if step_output["dependency_outputs"] != expected_dependencies:
        raise _divergence(
            "PREDECESSOR_OUTPUT_MISMATCH", expected=expected_dependencies,
            actual=step_output["dependency_outputs"],
        )
    return {
        **verdict,
        "campaign": observed,
        "output": {
            "step_id": step_id,
            "output_sha256": step_output["output_sha256"],
            "receipt_ref": step_output["skill_invocation_receipt_ref"],
            "provenance": "current-generation",
        },
    }


# --------------------------------------------------------------------------
# terminal receipt store: FAILED immutability + authorized retry (plan 7.1.3)
# --------------------------------------------------------------------------


def record_step_execution(store: dict[str, dict[str, Any]], step_output: Mapping[str, Any]) -> str:
    """Pure in-memory model of persisting a ``step-output/v1`` terminal,
    keyed by ``step_execution_id`` (plan 7.1.3: "Receipt terminal ... e
    imutavel e unico para aquele execution ID; terminal concorrente identico
    retorna REUSED, divergente e STATE_DIVERGENCE. FAILED nunca e
    sobrescrito por COMPLETED."). Mutates ``store`` only on a genuinely new
    execution ID or an identical replay; a divergent resubmission under the
    same ID is rejected and ``store`` is left byte-for-byte untouched.
    """
    validate_step_output(step_output)
    exec_id = step_output["step_execution_id"]
    existing = store.get(exec_id)
    if existing is None:
        store[exec_id] = dict(step_output)
        return "RECORDED"
    if existing["content_sha256"] == step_output["content_sha256"]:
        return "REUSED"
    raise _divergence(
        "TERMINAL_OVERWRITE_REJECTED",
        step_execution_id=exec_id,
        existing_result=existing["result"],
        attempted_result=step_output["result"],
    )


def retry_step_execution(
    store: dict[str, dict[str, Any]],
    failed_step_output: Mapping[str, Any],
    retry_step_output: Mapping[str, Any],
) -> str:
    """Authorize a retry of a ``FAILED`` terminal (plan 7.1.3). The retry
    must mint a brand-new ``step_execution_id`` carrying
    ``supersedes_step_execution_id`` back to the failed one, with an advanced
    ``execution_round``: it may never resubmit under the failed ID, and
    ``record_step_execution`` still refuses to let it overwrite the FAILED
    receipt already in the store.
    """
    validate_step_output(failed_step_output)
    validate_step_output(retry_step_output)
    _require(failed_step_output["result"] == "FAILED", "NOT_A_FAILED_TERMINAL", result=failed_step_output["result"])
    if retry_step_output["step_execution_id"] == failed_step_output["step_execution_id"]:
        raise _divergence("RETRY_REUSES_FAILED_EXECUTION_ID", step_execution_id=failed_step_output["step_execution_id"])
    if retry_step_output["supersedes_step_execution_id"] != failed_step_output["step_execution_id"]:
        raise _unattested(
            "RETRY_NOT_LINKED_TO_FAILED",
            expected=failed_step_output["step_execution_id"],
            actual=retry_step_output["supersedes_step_execution_id"],
        )
    if retry_step_output["execution_round"] <= failed_step_output["execution_round"]:
        raise _divergence(
            "RETRY_ROUND_NOT_ADVANCED",
            previous=failed_step_output["execution_round"],
            attempted=retry_step_output["execution_round"],
        )
    record_step_execution(store, failed_step_output)
    return record_step_execution(store, retry_step_output)


def supersede_step_execution(
    store: dict[str, dict[str, Any]],
    superseded_step_output: Mapping[str, Any],
    successor_step_output: Mapping[str, Any],
) -> str:
    """Authorize re-attestation of a step whose artefact legitimately changed.

    ``retry_step_execution`` already covers the failed case: a ``FAILED``
    terminal is replaced by a new attempt. The case it never covered is the
    terminal that *succeeded* and whose artefact was then legitimately
    corrected. Nothing could reconcile that, so a closed step stayed
    permanently divergent from the bytes it attested, and an auditor could no
    longer tell an honest correction from tampering -- which is precisely the
    distinction the chain exists to sustain (BL-0201).

    The answer takes the shape the envelope already reserved fields for. The
    prior terminal is never rewritten and never removed; a successor terminal
    is recorded that names what it replaces. Auditing then reads a history
    instead of a contradiction: the step's current receipt, and every receipt
    it supersedes, each still anchored on the bytes it actually saw.

    Superseding is deliberately not free. The successor must attest the same
    step, advance the round, carry both back-references, and actually differ:
    a successor identical to what it claims to replace is a no-op dressed as a
    correction, and is refused rather than silently recorded.

    What this does *not* decide is what happens to the steps downstream, whose
    own receipts named the output being replaced. That is the caller's ledger
    to keep, because only the caller knows the sequence; see the CLI's stale
    chain, which is what stops a superseded predecessor from reaching ``ship``
    unnoticed.
    """
    validate_step_output(superseded_step_output)
    validate_step_output(successor_step_output)
    _require(
        superseded_step_output["step_id"] == successor_step_output["step_id"],
        "SUPERSEDE_STEP_MISMATCH",
        superseded=superseded_step_output["step_id"],
        successor=successor_step_output["step_id"],
    )
    if successor_step_output["step_execution_id"] == superseded_step_output["step_execution_id"]:
        raise _divergence(
            "SUPERSEDE_REUSES_EXECUTION_ID",
            step_execution_id=superseded_step_output["step_execution_id"],
        )
    if successor_step_output["supersedes_step_execution_id"] != superseded_step_output["step_execution_id"]:
        raise _unattested(
            "SUPERSEDE_NOT_LINKED",
            expected=superseded_step_output["step_execution_id"],
            actual=successor_step_output["supersedes_step_execution_id"],
        )
    if successor_step_output["supersedes_attempt_id"] != superseded_step_output["attempt_id"]:
        raise _unattested(
            "SUPERSEDE_ATTEMPT_NOT_LINKED",
            expected=superseded_step_output["attempt_id"],
            actual=successor_step_output["supersedes_attempt_id"],
        )
    if successor_step_output["execution_round"] <= superseded_step_output["execution_round"]:
        raise _divergence(
            "SUPERSEDE_ROUND_NOT_ADVANCED",
            previous=superseded_step_output["execution_round"],
            attempted=successor_step_output["execution_round"],
        )
    # Not the receipt bytes: two receipts for the same artefact always differ in
    # bytes, because the round is part of what is hashed. What a correction has
    # to move is one of the two things a step receipt actually claims -- the
    # artefact it produced, or the predecessor output it rests on.
    #
    # Both matter. A step downstream of a corrected one is re-attested with its
    # own artefact byte-identical: nothing about its work changed, only which
    # predecessor now stands. Demanding a new artefact there would forbid the
    # very re-attestation that clears the stale chain.
    if (successor_step_output["output_sha256"] == superseded_step_output["output_sha256"]
            and successor_step_output["dependency_outputs"] == superseded_step_output["dependency_outputs"]):
        raise _divergence(
            "SUPERSEDE_WITHOUT_CHANGE",
            step_execution_id=superseded_step_output["step_execution_id"],
            output_sha256=superseded_step_output["output_sha256"],
        )
    record_step_execution(store, superseded_step_output)
    return record_step_execution(store, successor_step_output)
