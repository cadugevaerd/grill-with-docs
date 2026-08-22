#!/usr/bin/env python3
"""Coordinator-owned durable Gauntlet run primitives.

This is deliberately a small persistence boundary.  It accepts a proof which
the public adapter has already verified, records only coordinator transitions
through :func:`store.transact_with_event`, and never starts work.  Scheduling,
worker preparation and cleanup belong to later FASE-002 tasks.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

# ``grill_workspace`` loads core modules by file path, so this file cannot
# assume it has a package parent.  Keep the package import for normal library
# users, with the same descriptor-safe sibling loading convention as the
# other standalone core modules for the CLI path.
try:
    from . import store
except ImportError:
    _store_spec = importlib.util.spec_from_file_location(
        "grill_core._store", Path(__file__).resolve().with_name("store.py")
    )
    if _store_spec is None or _store_spec.loader is None:
        raise ImportError("unable to load grill_core store")
    store = importlib.util.module_from_spec(_store_spec)
    sys.modules[_store_spec.name] = store
    try:
        _store_spec.loader.exec_module(store)
    except BaseException:
        sys.modules.pop(_store_spec.name, None)
        raise


RUN_ID_RE = re.compile(r"^run-[A-Za-z0-9][A-Za-z0-9._-]*$")
WAVE_ID = "wave-0001"
# Every store.transact_with_event call, including admission's own, must name
# an ``event.wave_id`` that already exists in the candidate's ``waves`` map
# (store._candidate_transition) -- so admission still needs a placeholder
# wave-0001 record to correlate its own event to, even though no real
# membership is known yet.  This sentinel is never a real node id: it is
# overwritten wholesale, never merged, the moment declare_wave's first call
# activates wave-0001 with real node_ids (store.py's per-wave immutability
# check exempts a DECLARED-state record from the node_ids-cannot-change rule
# for exactly this reason -- see its own comment).
WAVE_PENDING_NODE_IDS = ["pending-declaration"]
# FASE-003 (FR-008(d)/FR-009): the single fixed lease grant/renewal duration.
# ``_new_coordinator_lease`` (first dispatch and remediation mints) and
# ``record_progress`` (every renewal) both anchor to this one constant, never
# a second one -- see their docstrings.
LEASE_DURATION = timedelta(hours=1)


class GauntletRunError(Exception):
    """Named domain denial for the public CLI adapter to translate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise GauntletRunError(code, message)


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(store.HEX64_RE.fullmatch(value))


def _hex40(value: Any) -> bool:
    return isinstance(value, str) and bool(store.HEX40_RE.fullmatch(value))


def admission_from_proof(
    *, activation: Mapping[str, Any], work_item_sha256: str, workflow_sha256: str,
    config_sha256: str, base_commit: str,
) -> dict[str, str]:
    """Convert a current FASE-001 activation proof into immutable run identity.

    ``activation`` is the exact activation record read by the adapter.  Hashing
    it here makes the identity independent of JSON presentation and keeps Store
    hash fields in their required bare-hex form.
    """
    if not isinstance(activation, Mapping):
        _fail("ACTIVATION-REQUIRED", "activation proof is missing")
    result = {
        "activation_sha256": store.jcs_sha256(dict(activation)),
        "work_item_sha256": work_item_sha256,
        "workflow_sha256": workflow_sha256,
        "config_sha256": config_sha256,
        "base_commit": base_commit,
    }
    _validate_admission(result)
    return result


_ADMISSION_IDENTITY_KEYS = ("activation_sha256", "work_item_sha256", "workflow_sha256", "config_sha256")


def _validate_admission(admission: Any) -> dict[str, str]:
    required = {"activation_sha256", "work_item_sha256", "workflow_sha256", "config_sha256", "base_commit"}
    if not isinstance(admission, Mapping) or set(admission) != required:
        _fail("ACTIVATION-REQUIRED", "admission identity is incomplete")
    result = dict(admission)
    if any(not _hex64(result[key]) for key in required - {"base_commit"}) or not _hex40(result["base_commit"]):
        _fail("ACTIVATION-REQUIRED", "admission identity is invalid")
    return result  # type: ignore[return-value]


def _require_base_commit(root: str | Path, admission: Mapping[str, str]) -> None:
    """Refuse a syntactically valid but non-existent Git revision."""
    try:
        check = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{admission['base_commit']}^{{commit}}"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as exc:
        _fail("BASE-COMMIT-UNAVAILABLE", "could not verify admission base commit")
    if check.returncode != 0:
        _fail("BASE-COMMIT-UNAVAILABLE", "admission base commit does not exist")


def _input_hash(admission: Mapping[str, str]) -> str:
    return store.jcs_sha256(dict(admission))


def _receipt_and_event(*, name: str, event_name: str, work_id: str, run_id: str,
                       admission: Mapping[str, str], wave_id: str = WAVE_ID) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = {
        "category": "runtime", "name": name, "work_id": work_id,
        "run_id": run_id, "wave_id": wave_id,
        "base_commit": admission["base_commit"],
        "input_sha256": _input_hash(admission), "output_sha256": None,
    }
    # Store binds and verifies this value against the exact durable payload.
    payload = {"category": receipt["category"], "name": receipt["name"], **{
        key: receipt[key] for key in ("work_id", "run_id", "wave_id", "base_commit", "input_sha256", "output_sha256")
    }}
    event = {
        "event": event_name, "work_id": work_id, "run_id": run_id,
        "wave_id": wave_id, "base_commit": admission["base_commit"],
        "input_sha256": receipt["input_sha256"], "output_sha256": None,
        "receipt_sha256": store.jcs_sha256(payload),
    }
    return receipt, event


def _matching_run(runs: Mapping[str, Any], admission: Mapping[str, str]) -> tuple[str, dict[str, Any]] | None:
    for run_id in sorted(runs):
        run = runs[run_id]
        if isinstance(run, dict) and run.get("admission") == dict(admission) and run.get("state") not in {"BLOCKED", "COMPLETE"}:
            return run_id, run
    return None


def _new_run_id(runs: Mapping[str, Any], admission: Mapping[str, str]) -> str:
    """Derive a safe, stable identifier without an entropy or clock dependency."""
    stem = hashlib.sha256(store.jcs(dict(admission))).hexdigest()[:24]
    candidate = f"run-{stem}"
    suffix = 1
    while candidate in runs:
        suffix += 1
        candidate = f"run-{stem}-{suffix}"
    return candidate


def _read_runs(root: str | Path, work_id: str, *, absent_ok: bool = False) -> dict[str, Any]:
    snapshot = store.read_snapshot(root)
    try:
        item = snapshot.document["work_items"][work_id]
    except (KeyError, TypeError):
        if absent_ok:
            return {}
        _fail("WORK-ITEM-NOT-FOUND", "work item is not registered in the Store")
    if not isinstance(item, dict):
        _fail("ORCHESTRATOR-INVALID", "work item record is invalid")
    block = item.get("gauntlet")
    if block is None:
        return {}
    if not isinstance(block, dict) or block.get("schema") != store.GAUNTLET_SCHEMA or not isinstance(block.get("runs"), dict):
        _fail("ORCHESTRATOR-INVALID", "durable Gauntlet state is invalid")
    return block["runs"]


_TRANSITION_COMMON = frozenset({
    "event", "work_id", "run_id", "wave_id", "base_commit",
    "input_sha256", "output_sha256", "receipt_sha256",
})
_TRANSITION_WORKER = frozenset({"worker_id", "lease_id", "fencing_token"})
_JOURNAL_ENVELOPE = frozenset({"recorded_at", "sequence", "previous_sha256", "content_sha256"})


def _evidence_failure(message: str) -> None:
    """Deny a status projection whose durable evidence is not self-consistent."""
    _fail("EVIDENCE-CORRELATION-INVALID", message)


def _find_transition_event(root: str | Path, work_id: str, run_id: str,
                           run: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve ``last_transition`` through the verified, coordinator journal.

    The snapshot keeps only the sequence plus bare digest.  Neither a worker
    supplied receipt path nor an unverified receipt name is a reference here:
    the coordinator's journal is the sole authority that connects them.
    """
    transition = run.get("last_transition")
    if not isinstance(transition, Mapping):
        _evidence_failure("run last transition is missing")
    sequence = transition.get("event_sequence")
    receipt_sha256 = transition.get("receipt_sha256")
    if type(sequence) is not int or sequence < 1 or not _hex64(receipt_sha256):
        _evidence_failure("run last transition is invalid")
    matches = [event for event in store.read_events(root) if event.get("sequence") == sequence]
    if len(matches) != 1:
        _evidence_failure("run last transition does not name one journal event")
    event = matches[0]
    if set(event) - _TRANSITION_COMMON - _TRANSITION_WORKER - _JOURNAL_ENVELOPE:
        _evidence_failure("transition contains non-coordinator fields")
    if not _TRANSITION_COMMON.issubset(event) or not str(event.get("event", "")).startswith("gauntlet."):
        _evidence_failure("transition is not a Gauntlet coordinator event")
    admission = run.get("admission")
    if not isinstance(admission, Mapping):
        _evidence_failure("run admission is invalid")
    if (
        event.get("work_id") != work_id
        or event.get("run_id") != run_id
        or event.get("base_commit") != admission.get("base_commit")
        or event.get("wave_id") not in run.get("waves", {})
        or event.get("receipt_sha256") != receipt_sha256
        or not _hex64(event.get("input_sha256"))
        or not _hex64(event.get("receipt_sha256"))
        or (event.get("output_sha256") is not None and not _hex64(event.get("output_sha256")))
    ):
        _evidence_failure("transition does not correlate to its run")
    present_worker = _TRANSITION_WORKER.intersection(event)
    if present_worker and present_worker != _TRANSITION_WORKER:
        _evidence_failure("worker transition authority is incomplete")
    if present_worker:
        workers = run.get("workers")
        worker = workers.get(event["worker_id"]) if isinstance(workers, Mapping) else None
        lease = worker.get("lease") if isinstance(worker, Mapping) else None
        if (
            not isinstance(worker, Mapping)
            or not isinstance(lease, Mapping)
            or lease.get("lease_id") != event["lease_id"]
            or lease.get("fencing_token") != event["fencing_token"]
        ):
            _evidence_failure("worker transition authority is not recorded by the coordinator")
    return event


def _verify_coordinator_receipt(root: str | Path, event: Mapping[str, Any]) -> None:
    """Prove the event's bare receipt digest names one immutable runtime receipt.

    Receipt names are intentionally not projected and are never accepted from
    callers.  This scan is read-only and only trusts bytes whose JCS digest and
    full correlation payload exactly match the journal event.
    """
    payload_keys = set(event) - {"event", "receipt_sha256"} - set(_JOURNAL_ENVELOPE)
    payload_tail = {key: event[key] for key in payload_keys}
    matches = 0
    category_dir = store.store_paths(root).receipts / "runtime"
    try:
        store._validate_directory(category_dir)
        entries = sorted(category_dir.iterdir())
    except (OSError, store.StoreError) as exc:
        _evidence_failure(f"coordinator receipt is unavailable: {exc}")
    for path in entries:
        if path.suffix != ".json":
            continue
        try:
            store._validate_regular(path)
            raw = store._read_regular(path)
            receipt = store.loads(store._decode(raw, path))
        except (OSError, store.StoreError, ValueError) as exc:
            _evidence_failure(f"coordinator receipt is unreadable: {exc}")
        if not isinstance(receipt, dict) or set(receipt) != {
            "category", "name", "work_id", "run_id", "wave_id", "base_commit", "input_sha256", "output_sha256",
            *(_TRANSITION_WORKER if _TRANSITION_WORKER.issubset(event) else ()),
        }:
            continue
        if receipt.get("category") != "runtime" or not isinstance(receipt.get("name"), str):
            continue
        expected = {"category": "runtime", "name": receipt["name"], **payload_tail}
        if receipt != expected:
            continue
        if raw != store.jcs(receipt) + b"\n" or store.jcs_sha256(receipt) != event["receipt_sha256"]:
            continue
        matches += 1
    if matches != 1:
        _evidence_failure("transition receipt is forged, missing, or mismatched")


def _project_last_transition(root: str | Path, work_id: str, run_id: str,
                             run: Mapping[str, Any]) -> dict[str, Any]:
    event = _find_transition_event(root, work_id, run_id, run)
    _verify_coordinator_receipt(root, event)
    projection = {
        key: event[key] for key in (
            "work_id", "run_id", "wave_id", "base_commit", "input_sha256", "output_sha256", "receipt_sha256"
        )
    }
    for key in ("worker_id", "lease_id", "fencing_token"):
        if key in event:
            projection[key] = event[key]
    return projection


_TRANSIENT_STORE_CODES = {store.STATE_DIVERGENCE, store.ORCHESTRATOR_INVALID}


def admit_or_reuse_run(root: str | Path, work_id: str, admission: Mapping[str, str], *,
                        _retry_budget: int = 2) -> dict[str, Any]:
    """Admission wrapper tolerant of Store's journal-before-snapshot window.

    A reader may briefly see the writer's journal anchor before its snapshot.
    That is intentionally fail-closed in Store; coordinator admission retries a
    bounded number of complete read/transaction attempts, then preserves the
    named Store block.  Each retry begins by re-reading and therefore reuses a
    peer's just-published identical run rather than appending another event.
    """
    try:
        return _admit_or_reuse_run_once(root, work_id, admission)
    except store.StoreError as exc:
        if exc.code not in _TRANSIENT_STORE_CODES or _retry_budget <= 0:
            raise
        return admit_or_reuse_run(root, work_id, admission, _retry_budget=_retry_budget - 1)


def _admit_or_reuse_run_once(root: str | Path, work_id: str, admission: Mapping[str, str]) -> dict[str, Any]:
    """Create one durable run, or reuse the compatible active run unchanged."""
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    # FASE-001 has deliberately no Store side effects.  Durable admission is
    # therefore the first explicit coordinator operation allowed to create
    # the project Store; it never takes ownership of another project identity.
    store.bootstrap(root)
    store.recover_pending_transition(root)
    runs = _read_runs(root, work_id, absent_ok=True)
    existing = _matching_run(runs, identity)
    if existing is not None:
        run_id, _ = existing
        return {"verdict": "RUN-REUSED", "work_id": work_id, "run_id": run_id, "base_commit": identity["base_commit"]}

    run_id = _new_run_id(runs, identity)
    receipt, event = _receipt_and_event(
        name=f"gauntlet-run-admit-{run_id}", event_name="gauntlet.run.admitted",
        work_id=work_id, run_id=run_id, admission=identity,
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        items = document.get("work_items")
        if not isinstance(items, dict):
            _fail("ORCHESTRATOR-INVALID", "Store work item map is invalid")
        item = items.get(work_id)
        if item is None:
            # The FASE-001 guard already proved this exact work id.  We store
            # only the minimal coordinator projection; no worktree is claimed.
            item = {"type": "feature", "slug": work_id, "lifecycle": "ACTIVE", "worktree": None, "monitoring": None}
            items[work_id] = item
        if not isinstance(item, dict):
            _fail("ORCHESTRATOR-INVALID", "Store work item record is invalid")
        block = item.setdefault("gauntlet", {"schema": store.GAUNTLET_SCHEMA, "runs": {}})
        if not isinstance(block, dict) or block.get("schema") != store.GAUNTLET_SCHEMA or not isinstance(block.get("runs"), dict):
            _fail("ORCHESTRATOR-INVALID", "durable Gauntlet state is invalid")
        # A compatible run appearing between the preliminary read and this
        # transaction is a conflict, never an accidental duplicate transition.
        if _matching_run(block["runs"], identity) is not None:
            _fail("ADMISSION-CONFLICT", "compatible run appeared during admission")
        block["runs"][run_id] = {
            "admission": copy.deepcopy(identity), "state": "ADMITTED", "recovery_count": 0,
            # A DECLARED placeholder, never real membership -- see
            # WAVE_PENDING_NODE_IDS.  declare_wave's first call overwrites
            # this wholesale with the actual requested node_ids.
            "waves": {WAVE_ID: {"state": "DECLARED", "node_ids": list(WAVE_PENDING_NODE_IDS)}}, "workers": {},
            "last_transition": {"event_sequence": 1, "receipt_sha256": "0" * 64},
        }
        return document

    try:
        store.transact_with_event(root, mutate, event=event, receipt=receipt)
    except GauntletRunError as exc:
        # A peer may have committed precisely the same admission after our
        # preliminary read.  Its failed transaction wrote nothing; re-read
        # only the authoritative Store and converge on that durable run.
        if exc.code != "ADMISSION-CONFLICT":
            raise
        concurrent = _matching_run(_read_runs(root, work_id), identity)
        if concurrent is None:
            raise
        return {
            "verdict": "RUN-REUSED", "work_id": work_id,
            "run_id": concurrent[0], "base_commit": identity["base_commit"],
        }
    return {"verdict": "RUN-CREATED", "work_id": work_id, "run_id": run_id, "base_commit": identity["base_commit"]}


def run_projection(root: str | Path, work_id: str, run_id: str | None = None) -> dict[str, Any] | None:
    """Return a deliberately read-only, stable public-shaped run projection."""
    if run_id is not None and (not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id)):
        _fail("RUN-NOT-FOUND", "run identifier is invalid")
    # A Store can legitimately have no entry for an activated FASE-001 item:
    # durable state has not been admitted yet.  That is a STATUS absence, not
    # a denial, unless the operator explicitly named a run to look up.
    try:
        runs = _read_runs(root, work_id, absent_ok=True)
    except store.StoreError:
        # Do not downgrade a malformed existing Store.  Only the literal
        # absence of its snapshot is the pre-admission STATUS condition.
        if store.store_paths(root).orchestrator.exists():
            raise
        if run_id is None:
            return None
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    if run_id is None:
        if not runs:
            return None
        run_id = sorted(runs)[-1]
    run = runs.get(run_id)
    if not isinstance(run, dict):
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    workers = []
    for worker_id in sorted(run.get("workers", {})):
        worker = run["workers"][worker_id]
        workers.append({
            "worker_id": worker_id, "state": worker.get("state"),
            "lease": copy.deepcopy(worker.get("lease")),
            # The grant is passive coordinator-recorded authority, not a
            # worker-provided capability claim.  It is safe to diagnose but
            # never supplies a Store or receipt reference.
            "grant": copy.deepcopy(worker.get("grant")),
            # FASE-003 (FR-010, T016/T018): the sole read-back path for a
            # FAILED worker's classification -- recovered from the immutable
            # receipt this module itself minted at the transition, never a
            # Store field (see ``terminate_worker``'s docstring).
            "failure_class": _read_worker_failure_class(root, work_id, run_id, run, worker_id, worker),
        })
    # FASE-004 (FR-011): wave membership and the open convergence block, read
    # straight off this same snapshot -- never the journal, never a receipt
    # probe, and never any worker diff content.
    records = run.get("waves", {})
    wave_ids = [wave_id for wave_id in sorted(records) if not _is_placeholder_wave(records[wave_id])]
    waves = []
    for wave_id in wave_ids:
        node_ids = records[wave_id].get("node_ids") or []
        waves.append({
            "wave_id": wave_id, "state": records[wave_id].get("state"),
            "converged_count": sum(1 for node_id in node_ids if _converged_lineage_head(run, node_id)),
            "member_count": len(node_ids),
        })
    # The newest wave is not the one to ask: wave N+1 is legitimately declared
    # while wave N's block is still open (ADR-0022), so this walks declaration
    # order backwards and stops at the first wave that still carries one.
    conflict = next(
        (records[wave_id]["last_conflict"] for wave_id in reversed(wave_ids)
         if isinstance(records[wave_id].get("last_conflict"), Mapping)),
        None,
    )
    projection = {
        "run_id": run_id, "state": run.get("state"), "recovery_count": run.get("recovery_count"),
        "base_commit": run.get("admission", {}).get("base_commit"), "workers": workers, "waves": waves,
        "last_transition": _project_last_transition(root, work_id, run_id, run),
    }
    if conflict is not None:
        projection["last_conflict"] = {"node_ids": list(conflict["node_ids"]), "reason": conflict["reason"]}
    return projection


def record_resume_decision(root: str | Path, work_id: str, run_id: str,
                           admission: Mapping[str, str]) -> dict[str, Any]:
    """Record the sole explicit recovery decision; it never relaunches work."""
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        _fail("RUN-NOT-FOUND", "run identifier is invalid")
    store.recover_pending_transition(root)
    runs = _read_runs(root, work_id)
    run = runs.get(run_id)
    if not isinstance(run, dict):
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    if run.get("admission") != identity:
        _fail("IDENTITY-STALE", "current activation differs from run admission")
    if run.get("state") == "RECOVERY_RECORDED" and run.get("recovery_count") == 1:
        return {"verdict": "RESUME-REUSED", "work_id": work_id, "run_id": run_id, "recovery_count": 1}
    if run.get("state") != "RECOVERY_ELIGIBLE" or run.get("recovery_count") != 0:
        _fail("RECOVERY-NOT-ELIGIBLE", "run has no eligible interrupted recovery")

    receipt, event = _receipt_and_event(
        name=f"gauntlet-resume-{run_id}", event_name="gauntlet.run.recovery-recorded",
        work_id=work_id, run_id=run_id, admission=identity,
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        try:
            candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        except (KeyError, TypeError):
            _fail("RUN-NOT-FOUND", "requested durable run does not exist")
        if candidate.get("admission") != identity:
            _fail("IDENTITY-STALE", "current activation differs from run admission")
        if candidate.get("state") != "RECOVERY_ELIGIBLE" or candidate.get("recovery_count") != 0:
            _fail("RECOVERY-NOT-ELIGIBLE", "run recovery changed before recording")
        candidate["state"] = "RECOVERY_RECORDED"
        candidate["recovery_count"] = 1
        return document

    try:
        store.transact_with_event(root, mutate, event=event, receipt=receipt)
    except GauntletRunError as exc:
        # As above, the only equivalent concurrent outcome is the immutable
        # one-time decision already recorded by another coordinator command.
        if exc.code != "RECOVERY-NOT-ELIGIBLE":
            raise
        concurrent = _read_runs(root, work_id).get(run_id)
        if not isinstance(concurrent, dict) or concurrent.get("admission") != identity:
            raise
        if concurrent.get("state") != "RECOVERY_RECORDED" or concurrent.get("recovery_count") != 1:
            raise
        return {"verdict": "RESUME-REUSED", "work_id": work_id, "run_id": run_id, "recovery_count": 1}
    return {"verdict": "RESUME-RECORDED", "work_id": work_id, "run_id": run_id, "recovery_count": 1}


# FASE-003 (FR-003, FR-004, FR-006, ADR-0018): Execution DAG validation.
#
# ``gauntlet-dag-validate`` is the fail-closed gate every ``agent-execute``
# dispatch must clear before any wave/worker/lease/grant state exists.  It
# never generates or repairs a DAG (ADR-0014) -- ``tasks`` owns that -- and it
# never touches the Store beyond the caller's own activation proof: it is
# pure/stateless, re-run as needed, and persists nothing.  ``declare_wave``
# below re-runs this exact structural/scope/tier logic inline rather than
# trusting a prior ``gauntlet-dag-validate`` call's result (plan.md Complexity
# Tracking: a stateless validator has nowhere durable to leave a "this DAG was
# already validated" fact, and re-running a side-effect-free check is cheap).
DAG_SCHEMA = "grill-gauntlet-execution-dag/v1"
_DAG_NODE_KEYS = frozenset({"id", "depends_on", "tier", "parallel", "files"})
TIER_ORDER = {"small": 0, "medium": 1, "large": 2}
# FR-002 SSOT: the tier order itself (small < medium < large) is intrinsic
# structure, not policy -- it stays a module constant.  The *floors* applied
# at each point (the ``agent-execute`` floor and its Markdown supplemental
# floor) are policy, pinned at FASE-001 activation in ``gauntlet.TIER_POLICY``
# / ``supplemental``; this module never duplicates those literals, and never
# imports the activation/config module either -- every caller resolves them
# once from its own current activation proof and threads them down
# explicitly, the same way ``declare_wave`` already threads
# ``activation_max_workers`` rather than reading config content itself.
# A node's own worker (Phase 3 scope: first dispatch only, no remediation
# machinery yet) is "ready to be depended on" once it reaches any state
# outside the non-terminal set -- success or failure alike, matching FR-005's
# "a worker that reaches a terminal state frees its slot" vocabulary exactly.
TERMINAL_WORKER_STATES = store.WORKER_STATES - store.NON_TERMINAL_WORKER_STATES
_WAVE_ID_RE = re.compile(r"^wave-(\d{4,})$")


def _is_safe_relative_path(value: Any) -> bool:
    """The shared repo-relative-path character/segment rule.

    Factored out of :func:`_strict_scopes` so the Execution DAG's ``files``
    entries and the DAG file location itself (``_repo_relative_path``) apply
    exactly the same escape-proof rule a worker grant scope already does,
    without duplicating the character class.
    """
    if (not isinstance(value, str) or not value or value.startswith("/")
            or "\\" in value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        return False
    pieces = value.split("/")
    return not (any(piece in {"", ".", ".."} for piece in pieces) or pieces[0] == ".git")


def _repo_relative_path(root: str | Path, value: Any, label: str) -> Path:
    if not _is_safe_relative_path(value):
        _fail("INVALID-IDENTIFIER", f"{label} is invalid")
    return Path(root) / value


def _load_execution_dag(root: str | Path, dag_path: Any) -> dict[str, Any]:
    path = _repo_relative_path(root, dag_path, "dag path")
    try:
        raw = path.read_bytes()
    except OSError:
        _fail("DAG-MALFORMED", "Execution DAG file is unavailable")
    try:
        document = json.loads(raw)
    except ValueError:
        _fail("DAG-MALFORMED", "Execution DAG is not valid JSON")
    return document


def _require_acyclic(nodes_by_id: Mapping[str, dict[str, Any]]) -> None:
    """Kahn's algorithm.  Any node left unresolved sits on a cycle -- this
    also catches a self-dependency, a one-node cycle, with no special case."""
    indegree = {node_id: len(node["depends_on"]) for node_id, node in nodes_by_id.items()}
    dependents: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
    for node_id, node in nodes_by_id.items():
        for dep in node["depends_on"]:
            dependents[dep].append(node_id)
    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    resolved = 0
    while ready:
        current = ready.pop()
        resolved += 1
        for dependent in sorted(dependents[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if resolved != len(nodes_by_id):
        _fail("DAG-CYCLIC", "Execution DAG contains a cycle")


def _validate_dag_structure(document: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(document, dict) or set(document) != {"schema", "feature", "max_workers", "nodes"}:
        _fail("DAG-MALFORMED", "Execution DAG document is invalid")
    if document["schema"] != DAG_SCHEMA:
        _fail("DAG-MALFORMED", "Execution DAG schema is unrecognized")
    if not isinstance(document["feature"], str) or not document["feature"]:
        _fail("DAG-MALFORMED", "Execution DAG feature is invalid")
    max_workers = document["max_workers"]
    if type(max_workers) is not int or max_workers < 1:
        _fail("DAG-MALFORMED", "Execution DAG max_workers is invalid")
    nodes = document["nodes"]
    if not isinstance(nodes, list) or not nodes:
        _fail("DAG-MALFORMED", "Execution DAG nodes are invalid")
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or set(node) != _DAG_NODE_KEYS:
            _fail("DAG-MALFORMED", "Execution DAG node is invalid")
        node_id = node["id"]
        if not isinstance(node_id, str) or not store.SAFE_NAME_RE.fullmatch(node_id):
            _fail("DAG-MALFORMED", "Execution DAG node id is invalid")
        if store.WORKER_REMEDIATION_SUFFIX_RE.fullmatch(node_id):
            _fail("DAG-MALFORMED", "Execution DAG node id uses the reserved remediation suffix")
        if node_id in nodes_by_id:
            _fail("DAG-MALFORMED", "Execution DAG node id is duplicated")
        depends_on = node["depends_on"]
        if (not isinstance(depends_on, list) or any(not isinstance(dep, str) for dep in depends_on)
                or len(set(depends_on)) != len(depends_on)):
            _fail("DAG-MALFORMED", "Execution DAG node depends_on is invalid")
        if node["parallel"] is not True and node["parallel"] is not False:
            _fail("DAG-MALFORMED", "Execution DAG node parallel flag is invalid")
        if node["tier"] not in TIER_ORDER:
            _fail("DAG-MALFORMED", "Execution DAG node tier is invalid")
        files = node["files"]
        if (not isinstance(files, list) or not files or len(set(files)) != len(files)
                or any(not _is_safe_relative_path(f) for f in files)):
            _fail("DAG-MALFORMED", "Execution DAG node files are invalid")
        nodes_by_id[node_id] = node
    for node in nodes_by_id.values():
        for dep in node["depends_on"]:
            if dep not in nodes_by_id:
                _fail("DAG-MALFORMED", "Execution DAG node depends_on references an unknown node")
    _require_acyclic(nodes_by_id)
    return nodes_by_id


def _dag_scope_violation(path: str) -> bool:
    """FR-004/ADR-0018's two closed rejection rules, evaluated on the full
    path at any depth -- never anchored to the repo root.

    Purely path-syntactic: it takes only a path string, never a DAG document,
    so it is the one shared helper every scope-rejection call site uses --
    ``_validate_dag_scope`` (a DAG node's declared ``files``), ``declare_
    worker`` (a caller's ``--files`` grant, checked against this same rule
    regardless of what the DAG node itself declares), and ``prepare_worker``
    (F1 fix: the same rule applied unconditionally to every ``--scope``,
    with no DAG document in scope at all -- see its docstring). Do not
    duplicate this path-matching logic at a new call site; call this."""
    pieces = path.split("/")
    if ".grill" in pieces:
        return True
    return any(pieces[i] == ".specify" and pieces[i + 1] == "reports" for i in range(len(pieces) - 1))


def _validate_dag_scope(nodes_by_id: Mapping[str, dict[str, Any]]) -> None:
    for node_id, node in nodes_by_id.items():
        if any(_dag_scope_violation(path) for path in node["files"]):
            _fail("DAG-NODE-OUT-OF-SCOPE", f"Execution DAG node targets out-of-scope evidence: {node_id}")


def _is_markdown_only(files: list[str]) -> bool:
    return all(path.endswith(".md") for path in files)


def _validate_dag_tiers(nodes_by_id: Mapping[str, dict[str, Any]], *,
                        agent_execute_floor: str, markdown_floor: str) -> None:
    for node_id, node in nodes_by_id.items():
        floor = markdown_floor if _is_markdown_only(node["files"]) else agent_execute_floor
        if TIER_ORDER[node["tier"]] < TIER_ORDER[floor]:
            _fail("DAG-NODE-TIER-UNRESOLVED", f"Execution DAG node tier does not satisfy its floor: {node_id}")


def _load_and_validate_dag(root: str | Path, dag_path: Any, *,
                           agent_execute_floor: str, markdown_floor: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    """The one place all three DAG validation stages run, in FR-004's order:
    (1) structural validity, (2) FR-004's two scope rules, (3) FR-006's tier
    floor.  Shared by ``validate_execution_dag`` and ``declare_wave`` so the
    latter never trusts a separate call's earlier result.  The two floors are
    the caller's own current activation-pinned tier policy (FR-002 SSOT) --
    never a literal duplicated in this module.

    FASE-004 (FR-004c): also returns the DAG's own content digest, computed
    from the parsed document with the same JCS primitive every admission,
    receipt and event digest in this module already uses -- so a run's pin
    is independent of the file's byte presentation, not of its meaning.
    """
    document = _load_execution_dag(root, dag_path)
    nodes_by_id = _validate_dag_structure(document)
    _validate_dag_scope(nodes_by_id)
    _validate_dag_tiers(nodes_by_id, agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor)
    return document, nodes_by_id, store.jcs_sha256(document)


def validate_execution_dag(root: str | Path, work_id: str, run_id: str, dag_path: Any,
                           admission: Mapping[str, str], *,
                           agent_execute_floor: str, markdown_floor: str) -> dict[str, Any]:
    """Fail-closed structural + FR-004/FR-006 validation of one Execution DAG.

    Pure/stateless beyond the caller's current activation proof: this proves
    identity (shape + a real Git base commit) exactly like every other public
    primitive, but it never reads the Store's run/worker state and never
    mutates anything.  ``run_id`` is accepted and echoed for the caller's own
    correlation, matching every other command's output shape -- validating a
    DAG's structure does not depend on any run-scoped Store fact.  The two
    tier floors are the caller's current activation-pinned tier policy
    (FR-002 SSOT), resolved once by the CLI adapter and threaded down here.
    """
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    document, nodes_by_id, dag_content_sha256 = _load_and_validate_dag(
        root, dag_path, agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
    )
    return {
        "verdict": "DAG-VALID", "work_id": work_id, "run_id": run_id,
        "max_workers": document["max_workers"], "dag_content_sha256": dag_content_sha256,
        "nodes": [
            {
                "id": node_id, "depends_on": list(node["depends_on"]),
                "parallel": node["parallel"], "tier": node["tier"],
            }
            for node_id, node in nodes_by_id.items()
        ],
    }


def _node_lineage_head_entry(run: Mapping[str, Any], node_id: str) -> tuple[str, Mapping[str, Any]] | None:
    """The node's current lineage-head ``(worker_id, worker)``, or ``None``
    if the node has no worker at all yet.

    A remediated node has more than one worker record sharing the same
    ``node_id``; only the one worker no sibling names via its own
    ``remediates`` field is the lineage head -- an earlier, superseded
    attempt is never authoritative for the node's own readiness/terminality
    (corrects the prior "at most one worker record exists per node id"
    assumption, which remediation always breaks).
    """
    workers = run.get("workers", {})
    remediated_by = {
        worker.get("remediates") for worker in workers.values()
        if isinstance(worker, dict) and worker.get("remediates") is not None
    }
    heads = [
        (worker_id, worker) for worker_id, worker in workers.items()
        if isinstance(worker, dict) and worker.get("node_id") == node_id and worker_id not in remediated_by
    ]
    return heads[0] if len(heads) == 1 else None


def _node_lineage_head(run: Mapping[str, Any], node_id: str) -> Mapping[str, Any] | None:
    entry = _node_lineage_head_entry(run, node_id)
    return entry[1] if entry is not None else None


def _node_ready(run: Mapping[str, Any], node_id: str) -> bool:
    """Whether ``node_id`` satisfies a dependent's readiness check: its
    current lineage-head worker exists and reached ``TERMINAL`` -- the
    success outcome -- specifically, never merely any terminal-class state.
    A ``FAILED``/``BLOCKED``/``CONFLICT``/``ORPHANED`` (never remediated to a
    success) lineage head must never satisfy a dependent's readiness check."""
    head = _node_lineage_head(run, node_id)
    return head is not None and head.get("state") == "TERMINAL"


def _allocate_wave_id(newest_wave_id: str) -> str:
    match = _WAVE_ID_RE.fullmatch(newest_wave_id)
    if match is None:
        _fail("ORCHESTRATOR-INVALID", "durable wave identity is invalid")
    # NOTE: past wave-9999 this emits wave-10000, a 5-digit id that breaks
    # lexicographic max()-based "newest wave" ordering against 4-digit ids.
    # Not reachable in practice -- it would require 10000 waves in one run.
    return f"wave-{int(match.group(1)) + 1:04d}"


def _validate_wave_node_ids(node_ids: Any) -> list[str]:
    if not isinstance(node_ids, (list, tuple)) or not node_ids:
        _fail("WAVE-NODES-REQUIRED", "at least one node id is required")
    result: list[str] = []
    for node_id in node_ids:
        if not isinstance(node_id, str) or not store.SAFE_NAME_RE.fullmatch(node_id):
            _fail("INVALID-IDENTIFIER", "wave node id is invalid")
        if node_id in result:
            _fail("WAVE-NODES-REQUIRED", "wave node ids must be unique")
        result.append(node_id)
    return result


def _overlapping_scope(nodes_by_id: Mapping[str, dict[str, Any]], node_ids: list[str]) -> list[str]:
    """FASE-004 (FR-002/FR-004b, ADR-0021): every node of ``node_ids`` that
    shares a declared DAG ``files`` entry with another one.

    The Execution DAG's own ``files`` is the source, never
    ``grant.scope_paths``: nothing compares a worker's ``--files`` grant
    against its DAG node's declaration, and FASE-003's own contract suite
    already exercises a deliberate divergence between the two.
    """
    overlapping: set[str] = set()
    for index, first in enumerate(node_ids):
        for second in node_ids[index + 1:]:
            if set(nodes_by_id[first]["files"]) & set(nodes_by_id[second]["files"]):
                overlapping.update((first, second))
    return sorted(overlapping)


def _is_placeholder_wave(wave: Any) -> bool:
    """Whether one wave record is admission's bootstrap sentinel rather than a
    wave anything was ever declared into.

    Both halves are load-bearing (FR-004c/FR-011): a wave record injected
    directly into the Store with ``state: DECLARED`` and real members is not
    the placeholder, and treating it as one would pin a DAG the run's existing
    waves never came from.  Through the public CLI only ``wave-0001`` in its
    admission-minted state ever satisfies this -- every later wave is born
    ``ACTIVE`` -- so this is equally the "is this entry real?" test
    :func:`run_projection` applies per wave and the "is the pin about to be
    written?" test :func:`declare_wave` applies to the newest one.
    """
    return (isinstance(wave, Mapping) and wave.get("state") == "DECLARED"
            and wave.get("node_ids") == list(WAVE_PENDING_NODE_IDS))


def _require_dag_pin(run: Mapping[str, Any], dag_content_sha256: str, *, expect_placeholder: bool = False) -> None:
    """FASE-004 (FR-001/FR-004c): the run's pinned DAG is the only DAG any
    later call may reason about.

    ``expect_placeholder`` is true on exactly one call per run -- the one
    replacing admission's bootstrap wave -- where the pin is about to be
    written rather than checked.  Every other call, including a run admitted
    before this field existed, must already carry it: adopting a later
    ``--dag`` retroactively would let FR-001's closing predicate run over a
    node set the run's earlier waves never came from, and ``COMPLETE`` is
    absorbing.
    """
    pinned = run.get("dag_content_sha256")
    if pinned is None:
        if not expect_placeholder:
            _fail("DAG-PIN-MISSING", "run has no pinned Execution DAG")
        return
    if pinned != dag_content_sha256:
        _fail("DAG-CONTENT-MISMATCH", "Execution DAG differs from the one pinned to this run")


def declare_wave(root: str | Path, work_id: str, run_id: str, dag_path: Any, node_ids: Any,
                 admission: Mapping[str, str], *, activation_max_workers: int,
                 agent_execute_floor: str, markdown_floor: str) -> dict[str, Any]:
    """Declare the run's next Execution Wave (FR-004, FR-005, ADR-0013).

    Re-validates the whole DAG inline (never trusts a prior ``gauntlet-dag-
    validate`` call), re-checks the named nodes' readiness (terminal
    dependencies) and ``parallel`` sharing rule against the run's current
    Store state, enforces the effective concurrent cap (the lesser of
    ``activation_max_workers`` -- resolved by the caller from the pinned
    activation record, this module never reads config content itself -- and
    the DAG's own declared ``max_workers``), and requires the run's current
    wave, if any, to already be ``COMPLETE`` before allocating a new one.

    The wave's Store record carries the actual, requested ``node_ids`` list,
    set once at wave creation and immutable for that wave's lifetime from
    that point on (B5 -- reverting an earlier substitution that recovered
    membership by scanning the journal for ``gauntlet.worker.declared``
    events instead; that scan made a wave member with no worker declared yet
    invisible to ``_wave_would_complete``, letting a wave complete while
    stranding a never-dispatched member).  Admission mints ``wave-0001`` as a
    ``DECLARED`` placeholder with no real membership (``store.transact_with_
    event`` requires every event's ``wave_id`` to already exist in the
    candidate, so admission's own event needs *something* to correlate to);
    this function's first call for a run overwrites that placeholder
    wholesale with real ``node_ids`` in the same ``DECLARED -> ACTIVE`` edge
    -- the one edge exempt from the node_ids-immutability rule, since nothing
    is really "declared" yet at that point (see ``store.py``'s own comment).
    ``WAVE-REUSED`` fires only from an actual concurrent-transaction race on
    the *same* target wave id (the same pattern :func:`admit_or_reuse_run`
    already uses) -- never as a guess about caller intent from wave state
    alone.
    """
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    if type(activation_max_workers) is not int or activation_max_workers < 1:
        _fail("INVALID-ARGUMENTS", "activation worker cap is invalid")
    requested = _validate_wave_node_ids(node_ids)
    document, nodes_by_id, dag_content_sha256 = _load_and_validate_dag(
        root, dag_path, agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
    )
    unknown = [node_id for node_id in requested if node_id not in nodes_by_id]
    if unknown:
        _fail("WAVE-NODE-UNKNOWN", f"wave names an unknown DAG node: {unknown[0]}")
    if len(requested) > 1 and any(not nodes_by_id[node_id]["parallel"] for node_id in requested):
        _fail("WAVE-NODE-NOT-PARALLEL", "a parallel:false node must dispatch alone")
    overlapping = _overlapping_scope(nodes_by_id, requested)
    if overlapping:
        _fail("WAVE-SCOPE-OVERLAP", f"wave members declare overlapping files: {', '.join(overlapping)}")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    for node_id in requested:
        for dep in nodes_by_id[node_id]["depends_on"]:
            if not _node_ready(run, dep):
                _fail("WAVE-NODE-NOT-READY", f"node dependency is not terminal: {node_id} depends on {dep}")

    waves = run.get("waves", {})
    newest_wave_id = max(waves)
    newest_state = waves[newest_wave_id].get("state")
    # The one legitimate overwrite: admission's placeholder record (or a
    # prior interrupted-and-retried declaration of it) has no real
    # membership yet -- this call replaces it wholesale, in place.  Both
    # halves are load-bearing (FR-004c): a Store-injected DECLARED record
    # carrying real members is not the bootstrap placeholder, and treating
    # it as one would pin a DAG the run's existing waves never came from.
    expect_placeholder = _is_placeholder_wave(waves[newest_wave_id])
    _require_dag_pin(run, dag_content_sha256, expect_placeholder=expect_placeholder)
    if newest_state == "ACTIVE":
        _fail("WAVE-PREREQUISITE-INCOMPLETE", "the run's current wave is not complete")
    if newest_state == "COMPLETE":
        target_wave_id = _allocate_wave_id(newest_wave_id)
    elif newest_state == "DECLARED":
        target_wave_id = newest_wave_id
    else:
        _fail("ORCHESTRATOR-INVALID", "durable wave state is invalid")

    non_terminal = sum(
        1 for worker in run.get("workers", {}).values()
        if isinstance(worker, dict) and worker.get("state") in store.NON_TERMINAL_WORKER_STATES
    )
    effective_cap = min(activation_max_workers, document["max_workers"])
    if non_terminal + len(requested) > effective_cap:
        _fail("WAVE-CAP-EXCEEDED", "wave would exceed the run's effective concurrent worker cap")

    receipt, event = _receipt_and_event(
        name=f"gauntlet-wave-declared-{run_id}-{target_wave_id}", event_name="gauntlet.wave.declared",
        work_id=work_id, run_id=run_id, admission=identity, wave_id=target_wave_id,
    )

    def activate(document_: dict[str, Any]) -> dict[str, Any]:
        candidate_run = document_["work_items"][work_id]["gauntlet"]["runs"][run_id]
        candidate_waves = candidate_run["waves"]
        if expect_placeholder:
            if candidate_waves.get(target_wave_id, {}).get("state") != "DECLARED":
                _fail("WAVE-CONFLICT", "wave changed before declaration")
        elif target_wave_id in candidate_waves:
            _fail("WAVE-CONFLICT", "wave appeared during declaration")
        candidate_waves[target_wave_id] = {"state": "ACTIVE", "node_ids": list(requested)}
        if expect_placeholder and "dag_content_sha256" not in candidate_run:
            candidate_run["dag_content_sha256"] = dag_content_sha256
        return document_

    try:
        store.transact_with_event(root, activate, event=event, receipt=receipt)
    except GauntletRunError as exc:
        if exc.code != "WAVE-CONFLICT":
            raise
        concurrent = _read_runs(root, work_id).get(run_id, {}).get("waves", {}).get(target_wave_id)
        # node_ids is now real, stored data (B5): a race is only a genuine
        # reuse of *this* request if the concurrently-committed wave named
        # the same members -- never a guess from state alone.
        if (isinstance(concurrent, dict) and concurrent.get("state") == "ACTIVE"
                and concurrent.get("node_ids") == requested):
            return {"verdict": "WAVE-REUSED", "work_id": work_id, "run_id": run_id, "wave_id": target_wave_id}
        raise
    return {"verdict": "WAVE-DECLARED", "work_id": work_id, "run_id": run_id, "wave_id": target_wave_id}


# Worktree preparation deliberately lives below the public adapter.  These
# helpers accept only logical identifiers and derive their one filesystem
# target from the common Git directory; callers cannot smuggle in a host path.
_GRANT_CAPABILITIES = ["git-local", "workspace-read-write"]


def _safe_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not store.SAFE_NAME_RE.fullmatch(value):
        _fail("INVALID-IDENTIFIER", f"{label} is invalid")
    return value


def _strict_scopes(scopes: Any) -> list[str]:
    if not isinstance(scopes, (list, tuple)) or not scopes:
        _fail("GRANT-INVALID", "at least one scoped path is required")
    result: list[str] = []
    for scope in scopes:
        if (not isinstance(scope, str) or not scope or scope.startswith("/")
                or "\\" in scope or any(ord(ch) < 32 or ord(ch) == 127 for ch in scope)):
            _fail("GRANT-INVALID", "grant scope path is invalid")
        pieces = scope.split("/")
        if any(piece in {"", ".", ".."} for piece in pieces) or pieces[0] == ".git":
            _fail("GRANT-INVALID", "grant scope path is invalid")
        if scope in result:
            _fail("GRANT-INVALID", "grant scope paths must be unique")
        result.append(scope)
    return result


def _workspace_identity(root: str | Path, work_id: str, run_id: str, worker_id: str,
                        admission: Mapping[str, str]) -> tuple[Path, dict[str, Any]]:
    _safe_name(work_id, "work item")
    _safe_name(run_id, "run")
    _safe_name(worker_id, "worker")
    key = f"wt-{run_id}-{worker_id}"
    # ``git_common_dir`` is descriptor-safe and insists that root is the
    # coordinator top-level.  ``key`` is a single validated logical segment.
    target = store.git_common_dir(root) / "grill" / key
    workspace = {
        "worktree_key": key,
        "branch": f"grill/{work_id}/{run_id}/{worker_id}",
        "base_commit": admission["base_commit"],
        "clean": True,
        "converged": False,
        "cleanup_eligible": False,
    }
    return target, workspace


def _git(root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["git", "-C", str(root), *args], stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        _fail("GIT-UNAVAILABLE", f"Git is unavailable: {exc}")


def _worktree_blocks(root: str | Path) -> list[list[str]]:
    process = _git(root, "worktree", "list", "--porcelain")
    if process.returncode != 0:
        _fail("GIT-UNAVAILABLE", "could not inspect Git worktrees")
    return [block.splitlines() for block in process.stdout.strip().split("\n\n") if block.strip()]


def _workspace_git_state(root: str | Path, target: Path, workspace: Mapping[str, Any]) -> str:
    """Classify only the exact declared Git identity; never discover a target."""
    if target.is_symlink():
        return "DIVERGENT"
    target_real = str(target.resolve(strict=False))
    branch = str(workspace["branch"])
    base = str(workspace["base_commit"])
    target_exists = target.exists() or target.is_symlink()
    branch_exists = _git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
    matching: list[list[str]] = []
    branch_registered = False
    branch_blocks = 0
    for block in _worktree_blocks(root):
        path_line = next((line for line in block if line.startswith("worktree ")), None)
        if path_line is None:
            continue
        registered_path = str(Path(path_line[9:]).resolve(strict=False))
        if f"branch refs/heads/{branch}" in block:
            branch_registered = True
            branch_blocks += 1
        if registered_path == target_real:
            matching.append(block)
    exact = (len(matching) == 1 and f"HEAD {base}" in matching[0]
             and f"branch refs/heads/{branch}" in matching[0])
    if exact and target_exists and branch_exists and branch_blocks == 1:
        return "EXACT"
    if not target_exists and not branch_exists and not matching and not branch_registered:
        return "ABSENT"
    return "DIVERGENT"


def _workspace_target_absent(root: str | Path, target: Path, workspace: Mapping[str, Any]) -> bool:
    """Whether cleanup's sole declared target is gone.

    ``git worktree remove`` intentionally leaves its local branch behind.  A
    retained *unregistered* branch is therefore not evidence of a partial
    removal; a registration at this target or on the declared branch is.
    """
    if target.exists() or target.is_symlink():
        return False
    target_real = str(target.resolve(strict=False))
    branch_marker = f"branch refs/heads/{workspace['branch']}"
    for block in _worktree_blocks(root):
        path_line = next((line for line in block if line.startswith("worktree ")), None)
        if path_line is not None and str(Path(path_line[9:]).resolve(strict=False)) == target_real:
            return False
        if branch_marker in block:
            return False
    return True


def _porcelain_entries(target: str | Path) -> list[str] | None:
    """One ``--untracked-files=all`` status read, or ``None`` if Git refused.

    ``-uall`` rather than the tool's ``-unormal`` default: the default
    collapses a wholly untracked directory into a single ``?? pkg/`` entry,
    which can never be matched against the file paths a worker's own diff
    names -- see :func:`converge_wave`'s untracked-collision pre-check.
    """
    status = _git(target, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        return None
    return [line for line in status.stdout.splitlines() if line.strip()]


def _untracked_paths(entries: list[str]) -> set[str]:
    return {entry[3:] for entry in entries if entry.startswith("?? ")}


def _exact_worktree_is_clean(root: str | Path, target: Path, *, include_untracked: bool = True) -> bool:
    """Prove the registered linked worktree has no tracked or untracked dirt.

    ``include_untracked=False`` narrows this to tracked content alone, for
    the one caller (:func:`converge_wave`) whose target is the coordinator's
    own control checkout: that checkout routinely carries untracked scratch
    and spec files which must never block convergence by themselves.  The
    default preserves ``cleanup_worker``'s strict, destructive-intent gate.
    """
    entries = _porcelain_entries(target)
    if entries is None:
        return False
    if include_untracked:
        return not entries
    return not [entry for entry in entries if not entry.startswith("?? ")]


def _worker_receipt_event(name: str, event_name: str, work_id: str, run_id: str,
                          admission: Mapping[str, str], worker_id: str,
                          lease: Mapping[str, Any], wave_id: str = WAVE_ID) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build worker-scoped evidence bound to the coordinator lease fence."""
    receipt, event = _receipt_and_event(name=name, event_name=event_name, work_id=work_id,
                                        run_id=run_id, admission=admission, wave_id=wave_id)
    lease_id, fencing_token = lease.get("lease_id"), lease.get("fencing_token")
    if (not isinstance(lease_id, str) or not store.SAFE_NAME_RE.fullmatch(lease_id)
            or type(fencing_token) is not int or fencing_token <= 0):
        _fail("LEASE-INVALID", "worker transition has no valid coordinator lease")
    event.update({"worker_id": worker_id, "lease_id": lease_id, "fencing_token": fencing_token})
    # Store's receipt payload intentionally retains event worker authority
    # while its public receipt locator remains closed and coordinator-owned.
    event["receipt_sha256"] = store.jcs_sha256(store._receipt_payload(event, receipt))
    return receipt, event


def _run_for_worker(root: str | Path, work_id: str, run_id: str,
                    admission: Mapping[str, str]) -> dict[str, Any]:
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    if not RUN_ID_RE.fullmatch(run_id):
        _fail("RUN-NOT-FOUND", "run identifier is invalid")
    run = _read_runs(root, work_id).get(run_id)
    if not isinstance(run, dict):
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    run_admission = run.get("admission")
    if (not isinstance(run_admission, Mapping)
            or any(run_admission.get(key) != identity[key] for key in _ADMISSION_IDENTITY_KEYS)):
        _fail("IDENTITY-STALE", "current activation differs from run admission")
    if run.get("state") in {"BLOCKED", "COMPLETE"}:
        _fail("RUN-NOT-ELIGIBLE", "run is not eligible for worker preparation")
    return run


def _transition_worker(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                       *, name: str, event_name: str, worker_id: str,
                       lease: Mapping[str, Any], mutate: Any, wave_id: str = WAVE_ID) -> None:
    receipt, event = _worker_receipt_event(name, event_name, work_id, run_id, admission, worker_id, lease, wave_id=wave_id)
    store.transact_with_event(root, mutate, event=event, receipt=receipt)


def _prepared_response(work_id: str, run_id: str, worker_id: str, workspace: Mapping[str, Any], *, reused: bool = False) -> dict[str, Any]:
    result = {"verdict": "REUSED" if reused else "WORKER-PREPARED", "work_id": work_id,
              "run_id": run_id, "worker_id": worker_id}
    if not reused:
        result.update({"worktree_key": workspace["worktree_key"], "base_commit": workspace["base_commit"]})
    return result


def _same_workspace_identity(recorded: Any, expected: Mapping[str, Any]) -> bool:
    return isinstance(recorded, Mapping) and all(
        recorded.get(key) == expected[key] for key in ("worktree_key", "branch", "base_commit")
    )


def _new_coordinator_lease(run_id: str, worker_id: str) -> dict[str, Any]:
    started = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "lease_id": f"lease-{run_id}-{worker_id}", "fencing_token": 1,
        "acquired_at": started.isoformat().replace("+00:00", "Z"),
        "expires_at": (started + LEASE_DURATION).isoformat().replace("+00:00", "Z"),
        "state": "ACTIVE", "recovery_count": 0,
    }


def _parse_rfc3339(value: Any, code: str = "LEASE-INVALID") -> datetime:
    if not isinstance(value, str):
        _fail(code, "timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, "timestamp is invalid")
    if parsed.tzinfo is None:
        _fail(code, "timestamp is invalid")
    return parsed


def _last_activity_at(lease: Mapping[str, Any]) -> datetime:
    """The timestamp of a worker's dispatch, or its most recent recorded
    progress transition, whichever is later -- derived, not stored.

    Both ``_new_coordinator_lease`` (dispatch) and ``record_progress`` (every
    renewal) set ``lease.expires_at`` to ``<event time> + LEASE_DURATION``.
    Subtracting the same fixed duration back out therefore always recovers
    the exact timestamp of the *last* of those two kinds of event, with no
    separate ``last_progress_at`` Store field needed.
    """
    return _parse_rfc3339(lease.get("expires_at")) - LEASE_DURATION


def _require_active_lease(lease: Mapping[str, Any]) -> None:
    """Refuse implicit worker recovery from a stale coordinator lease."""
    if lease.get("state") != "ACTIVE":
        _fail("LEASE-NOT-ACTIVE", "worker lease is not active; explicit recovery is required")
    expires_at = lease.get("expires_at")
    if not isinstance(expires_at, str):
        _fail("LEASE-NOT-ACTIVE", "worker lease expiration is invalid")
    try:
        expiration = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        _fail("LEASE-NOT-ACTIVE", "worker lease expiration is invalid")
    if expiration.tzinfo is None or expiration <= datetime.now(timezone.utc):
        _fail("LEASE-NOT-ACTIVE", "worker lease has expired; explicit recovery is required")


def prepare_worker(root: str | Path, work_id: str, run_id: str, worker_id: str,
                   scope_paths: Any, admission: Mapping[str, str], *,
                   node_id: str | None = None, remediates: str | None = None,
                   wave_id: str | None = None) -> dict[str, Any]:
    """Persist a worktree intent, make exactly that Git worktree, then finalize.

    This deliberately contains no dispatch or process launch.  An interrupted
    intent is reconciled only when all three Git identities (path, branch,
    base) are exact; anything partial is retained as ORPHANED.

    FASE-003 (FR-007) threads the node lineage a worker's record must now
    carry: ``node_id`` defaults to ``worker_id`` itself (a node's first
    dispatch sets ``worker_id = node_id`` verbatim) and ``remediates``
    defaults to ``None`` (first dispatch, never a remediation replacement).
    ``wave_id`` defaults to the FASE-002 module constant so the existing
    ``gauntlet-prepare-worker`` CLI -- which never passes any of these three
    keyword arguments -- keeps its exact prior behaviour and output.

    F1 fix (operator-approved, see plan.md's note on this and DECISION-
    BACKLOG.md BL-0002): every ``scope_paths``/``--scope`` entry is rejected,
    unconditionally, against ``_dag_scope_violation``'s two FR-004/ADR-0018
    rules -- no DAG document is needed or consulted, since the rule is
    purely path-syntactic (see that helper's docstring). This closes the
    self-attestation gap the existing ``gauntlet-prepare-worker`` command
    left open since FASE-002: nothing previously stopped a caller from
    minting a worker with write-scope grant over ``.grill/`` (where this
    very attestation chain lives) or ``.specify/reports/``, even though
    ``declare_worker`` -- the FASE-003 sibling command over this exact same
    Store -- has always rejected precisely that. This is a deliberate
    behavior change to the FASE-002 command surface, not a bug fix disguised
    as one: a ``--scope`` that previously succeeded silently now blocks with
    ``GRANT-OUT-OF-SCOPE``, a code distinct from ``declare_worker``'s
    ``DAG-NODE-OUT-OF-SCOPE`` because this call site has no DAG node to
    blame for the rejection.
    """
    identity = _validate_admission(admission)
    worker_id = _safe_name(worker_id, "worker")
    resolved_node_id = _safe_name(node_id, "node") if node_id is not None else worker_id
    if remediates is not None and not isinstance(remediates, str):
        _fail("INVALID-IDENTIFIER", "remediates is invalid")
    resolved_wave_id = wave_id if wave_id is not None else WAVE_ID
    scopes = _strict_scopes(scope_paths)
    if any(_dag_scope_violation(path) for path in scopes):
        _fail("GRANT-OUT-OF-SCOPE", "worker grant targets out-of-scope evidence")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    target, expected_workspace = _workspace_identity(root, work_id, run_id, worker_id, identity)
    existing = run.get("workers", {}).get(worker_id)
    if existing is not None and not isinstance(existing, dict):
        _fail("WORKER-INVALID", "worker record is invalid")
    if isinstance(existing, dict):
        if existing.get("node_id") != resolved_node_id or existing.get("remediates") != remediates:
            _fail("WORKER-CONFLICT", "worker declaration differs from requested node lineage")
        if existing.get("state") == "PREPARED":
            if existing.get("workspace") != expected_workspace or existing.get("grant") != {"scope_paths": scopes, "capabilities": _GRANT_CAPABILITIES}:
                _fail("WORKER-CONFLICT", "worker declaration differs from requested grant")
            if _workspace_git_state(root, target, expected_workspace) != "EXACT":
                _fail("WORKSPACE-PRESERVED", "prepared worker worktree is not exact")
            return _prepared_response(work_id, run_id, worker_id, expected_workspace, reused=True)
        if existing.get("state") == "ORPHANED":
            _fail("WORKSPACE-PRESERVED", "orphaned worker is preserved")
        if existing.get("state") not in {"DECLARED", "PREPARING"}:
            _fail("WORKER-CONFLICT", "worker is not preparable")
        declared_workspace = existing.get("workspace")
        declared_grant = existing.get("grant")
        if ((declared_workspace is not None and not _same_workspace_identity(declared_workspace, expected_workspace))
                or (declared_grant is not None and declared_grant != {"scope_paths": scopes, "capabilities": _GRANT_CAPABILITIES})):
            _fail("WORKER-CONFLICT", "worker declaration differs from requested grant")
    else:
        lease = _new_coordinator_lease(run_id, worker_id)
        if remediates is not None:
            # FR-007/FR-008(e): a remediation worker's budget is minted
            # already spent -- the Store rejects any mint where this fact
            # disagrees with `remediates`' presence.
            lease["recovery_count"] = 1
        def declare(document: dict[str, Any]) -> dict[str, Any]:
            candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
            if worker_id in candidate["workers"]:
                _fail("WORKER-CONFLICT", "worker appeared during declaration")
            candidate["workers"][worker_id] = {
                "state": "DECLARED", "lease": copy.deepcopy(lease), "grant": None, "workspace": None,
                "node_id": resolved_node_id, "remediates": remediates,
            }
            return document
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-declared-{run_id}-{worker_id}", event_name="gauntlet.worker.declared", worker_id=worker_id, lease=lease, mutate=declare, wave_id=resolved_wave_id)

    # Declare the intent separately so no Store snapshot can claim a Git
    # effect before it exists.
    current = _run_for_worker(root, work_id, run_id, identity)["workers"][worker_id]
    current_lease = current.get("lease")
    if not isinstance(current_lease, Mapping):
        # Reconcile an older interrupted PREPARING intent by first recording
        # the coordinator lease it lacked.  The repair itself is worker-scoped
        # evidence, so every subsequent Git effect has a durable fence.
        repaired_lease = _new_coordinator_lease(run_id, worker_id)
        if remediates is not None:
            repaired_lease["recovery_count"] = 1
        expected_state = current.get("state")
        if expected_state not in {"DECLARED", "PREPARING"}:
            _fail("LEASE-INVALID", "worker has no coordinator lease")
        def establish_lease(document: dict[str, Any]) -> dict[str, Any]:
            candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            if candidate.get("state") != expected_state or candidate.get("lease") is not None:
                _fail("WORKER-CONFLICT", "worker changed before lease reconciliation")
            candidate["lease"] = copy.deepcopy(repaired_lease)
            return document
        _transition_worker(root, work_id, run_id, identity,
                           name=f"gauntlet-worker-lease-established-{run_id}-{worker_id}",
                           event_name="gauntlet.worker.lease-established", worker_id=worker_id,
                           lease=repaired_lease, mutate=establish_lease, wave_id=resolved_wave_id)
        current = _run_for_worker(root, work_id, run_id, identity)["workers"][worker_id]
        current_lease = current.get("lease")
    if not isinstance(current_lease, Mapping):
        _fail("LEASE-INVALID", "worker has no coordinator lease")
    _require_active_lease(current_lease)
    if current["state"] == "DECLARED":
        def preparing(document: dict[str, Any]) -> dict[str, Any]:
            worker = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            if worker.get("state") != "DECLARED": _fail("WORKER-CONFLICT", "worker changed before preparation")
            worker.update({"state": "PREPARING", "grant": {"scope_paths": scopes, "capabilities": _GRANT_CAPABILITIES}, "workspace": copy.deepcopy(expected_workspace)})
            return document
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-preparing-{run_id}-{worker_id}", event_name="gauntlet.worker.preparing", worker_id=worker_id, lease=current_lease, mutate=preparing, wave_id=resolved_wave_id)
    elif current["state"] != "PREPARING":
        _fail("WORKER-CONFLICT", "worker is not preparable")

    state = _workspace_git_state(root, target, expected_workspace)
    if state == "DIVERGENT":
        def orphan(document: dict[str, Any]) -> dict[str, Any]:
            worker = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            if worker.get("state") != "PREPARING": _fail("WORKER-CONFLICT", "worker changed during reconciliation")
            worker["state"] = "ORPHANED"; return document
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-orphaned-{run_id}-{worker_id}", event_name="gauntlet.worker.orphaned", worker_id=worker_id, lease=current_lease, mutate=orphan, wave_id=resolved_wave_id)
        _fail("WORKSPACE-PRESERVED", "partial worker worktree is preserved")
    if state == "ABSENT":
        # Re-check after the durable PREPARING intent: it must never act as
        # an implicit lease renewal if time passed while recording evidence.
        _require_active_lease(current_lease)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        added = _git(root, "worktree", "add", "-b", expected_workspace["branch"], str(target), expected_workspace["base_commit"])
        if added.returncode != 0:
            _fail("WORKTREE-CREATE-FAILED", "could not create isolated worker worktree")
    if _workspace_git_state(root, target, expected_workspace) != "EXACT":
        _fail("WORKSPACE-PRESERVED", "worker worktree did not match its declared identity")

    def prepared(document: dict[str, Any]) -> dict[str, Any]:
        worker = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
        if worker.get("state") != "PREPARING": _fail("WORKER-CONFLICT", "worker changed before finalization")
        worker["state"] = "PREPARED"
        # A newly-created linked worktree is clean by construction.  The
        # other two cleanup predicates remain false until their later owners
        # record convergence and eligibility.
        worker["workspace"]["clean"] = True
        return document
    _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-prepared-{run_id}-{worker_id}", event_name="gauntlet.worker.prepared", worker_id=worker_id, lease=current_lease, mutate=prepared, wave_id=resolved_wave_id)
    return _prepared_response(work_id, run_id, worker_id, expected_workspace)


def _resolve_worker_model(runtime: str, tier: str) -> dict[str, Any]:
    """Resolve the model a worker of this tier runs, or refuse.

    Deliberately fails closed on an unreadable or half-filled binding: falling
    back to "whatever the caller is running" is how a worker silently gets a
    frontier model.
    """
    try:  # normal library use, as a package
        from . import tier_models
    except ImportError:  # pragma: no cover - direct-file load
        spec = importlib.util.spec_from_file_location(
            "grill_core_tier_models", Path(__file__).resolve().parent / "tier_models.py"
        )
        tier_models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tier_models)
    try:
        return tier_models.resolve_model(runtime, tier, actor_class="worker")
    except tier_models.TierModelError as error:
        _fail(error.code, error.message)


def declare_worker(root: str | Path, work_id: str, run_id: str, node_id: str, wave_id: str,
                   tier: str, scope_paths: Any, dag_path: Any, admission: Mapping[str, str], *,
                   agent_execute_floor: str, markdown_floor: str,
                   runtime: str = "claude") -> dict[str, Any]:
    """FASE-003 first dispatch: ``worker_id = node_id`` verbatim, never a
    remediation (FR-007) -- remediation dispatch is ``gauntlet-remediate``,
    a later phase, and takes no ``--remediates``-shaped input here at all.

    A thin, named entry over :func:`prepare_worker`'s existing FASE-002
    intent protocol (``DECLARED -> PREPARING -> git worktree add ->
    PREPARED``) -- see its docstring for the full sequence; this function
    does not duplicate it.  It additionally: (1) rejects a ``node_id`` using
    the reserved remediation suffix, which no first dispatch may ever use;
    (2) re-checks FR-006's tier floor against the caller-declared
    ``tier``/``scope_paths`` pair; (3) rejects a grant (``scope_paths``)
    matching either of FR-004's two DAG-scope rejection rules (B3 fix) --
    ``declare_wave`` already enforces this against a DAG node's own declared
    ``files``, but nothing previously applied it to the grant a caller hands
    directly to this command, letting a caller mint a worker scoped to
    ``.grill/`` or ``.specify/reports/`` regardless of what the DAG says;
    (4) loads and validates the named DAG (B4 fix) and requires ``node_id``
    to actually be a member of the named wave's ``node_ids`` (a real,
    required Store field as of the B5 fix) rather than trusting a bare
    ``--node-id`` the caller could point at any not-ready or non-member node;
    (5) requires the named ``wave_id`` to name a wave of this run that is
    currently ``ACTIVE`` -- i.e. one ``declare_wave`` actually declared --
    rather than a pristine, never-declared, or already-``COMPLETE`` wave; and
    (6) requires every one of that node's DAG-declared ``depends_on`` to have
    a terminal (specifically ``TERMINAL``, the success outcome) lineage-head
    worker in the run, exactly like ``declare_wave`` already requires for a
    wave's own named nodes -- closing the gap where a direct
    ``gauntlet-worker-declare`` call could dispatch a not-ready node
    ``gauntlet-wave-declare`` would have refused to admit into a wave.
    """
    node_id = _safe_name(node_id, "node")
    if store.WORKER_REMEDIATION_SUFFIX_RE.fullmatch(node_id):
        _fail("INVALID-IDENTIFIER", "node id uses the reserved remediation suffix")
    wave_id = _safe_name(wave_id, "wave")
    scopes = _strict_scopes(scope_paths)
    if any(_dag_scope_violation(path) for path in scopes):
        _fail("DAG-NODE-OUT-OF-SCOPE", "worker grant targets out-of-scope evidence")
    if tier not in TIER_ORDER:
        _fail("DAG-NODE-TIER-UNRESOLVED", "worker tier is invalid")
    floor = markdown_floor if _is_markdown_only(scopes) else agent_execute_floor
    if TIER_ORDER[tier] < TIER_ORDER[floor]:
        _fail("DAG-NODE-TIER-UNRESOLVED", "worker tier does not satisfy its floor")
    # ADR-0013: the worker's model is DERIVED from its tier, never chosen by
    # the caller -- this function takes no --model at all. A frontier model for
    # actor class `worker` is refused here, before any lease, grant or worktree
    # exists, so a forbidden dispatch leaves nothing behind to clean up.
    model = _resolve_worker_model(runtime, tier)
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    wave = run.get("waves", {}).get(wave_id)
    if not isinstance(wave, dict) or wave.get("state") != "ACTIVE":
        _fail("WAVE-NOT-FOUND", "named wave is not an active wave of this run")
    _, nodes_by_id, _ = _load_and_validate_dag(
        root, dag_path, agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
    )
    if node_id not in nodes_by_id:
        _fail("WAVE-NODE-UNKNOWN", f"node is not part of the Execution DAG: {node_id}")
    if node_id not in wave.get("node_ids", []):
        _fail("WAVE-NODE-NOT-MEMBER", f"node is not a member of the named wave: {node_id}")
    for dep in nodes_by_id[node_id]["depends_on"]:
        if not _node_ready(run, dep):
            _fail("WAVE-NODE-NOT-READY", f"node dependency is not terminal: {node_id} depends on {dep}")
    prepared = prepare_worker(
        root, work_id, run_id, node_id, scopes, admission,
        node_id=node_id, remediates=None, wave_id=wave_id,
    )
    # Reported, not stored: the worker record's key set is closed and already
    # written in the field, so widening it is a separate, migrating change.
    # The control that matters -- the refusal -- already happened above, before
    # any durable state existed. Recording the resolved model durably is
    # declared debt, not a silent omission.
    return {**prepared, "model": model["model"], "model_frontier": model["frontier"],
            "model_runtime": model["runtime"]}


# FASE-003 (FR-008(d), FR-009, FR-010, ADR-0012, ADR-0015; T017-T019): progress
# recording, worker termination (with wave-completion detection), and stall
# remediation.  All three require the target worker in ``PREPARED`` -- the
# only non-terminal state a first-dispatch or remediation worker settles into
# once its worktree exists -- and resolve their own ``wave_id`` rather than
# accepting one from the caller (none of the three CLI commands take a
# ``--wave-id``): see ``_worker_wave_id``.
FAILURE_CLASSES = frozenset({"process-timeout", "transport-failure"})


def _failed_receipt_name(run_id: str, worker_id: str, failure_class: str) -> str:
    return f"gauntlet-worker-failed-{run_id}-{worker_id}-{failure_class}"


def _read_worker_failure_class(root: str | Path, work_id: str, run_id: str,
                               run: Mapping[str, Any], worker_id: str, worker: Mapping[str, Any]) -> str | None:
    """Recover FR-010's classification from the coordinator's own immutable
    evidence, for ``gauntlet-status`` (T016) -- see ``terminate_worker``'s
    docstring for why it lives in the receipt name rather than a Store field.
    A caller-asserted value is never trusted: the receipt bytes on disk must
    exactly match this worker's own recorded FAILED transition.
    """
    if worker.get("state") != "FAILED":
        return None
    lease = worker.get("lease")
    admission = run.get("admission")
    if not isinstance(lease, Mapping) or not isinstance(admission, Mapping):
        return None
    for failure_class in sorted(FAILURE_CLASSES):
        name = _failed_receipt_name(run_id, worker_id, failure_class)
        path = store.receipt_path(root, "runtime", name)
        try:
            store._validate_regular(path)
            raw = store._read_regular(path)
            receipt = store.loads(store._decode(raw, path))
        except (OSError, store.StoreError, ValueError):
            continue
        if not isinstance(receipt, dict):
            continue
        wave_id = receipt.get("wave_id")
        expected = {
            "category": "runtime", "name": name, "work_id": work_id, "run_id": run_id,
            "wave_id": wave_id, "base_commit": admission.get("base_commit"),
            "input_sha256": _input_hash(admission), "output_sha256": None,
            "worker_id": worker_id, "lease_id": lease.get("lease_id"),
            "fencing_token": lease.get("fencing_token"),
        }
        if receipt != expected or wave_id not in run.get("waves", {}):
            continue
        if raw != store.jcs(receipt) + b"\n":
            continue
        return failure_class
    return None


def _worker_wave_id(root: str | Path, work_id: str, run_id: str, worker_id: str) -> str:
    """Recover one worker's own declaration ``wave_id`` from the journal.

    FASE-003 (T023, B1 fix): a worker's own wave may already be ``COMPLETE``
    by the time this worker needs to record progress, terminate, or be
    remediated -- e.g. terminating a wave's last non-terminal node can
    complete the wave in the very same transaction as a sibling failure now
    being remediated, and a remediation replacement worker (``T1-r1``) can
    easily be minted after its wave already went ``COMPLETE`` (the rest of
    the wave finished while the original worker was being remediated).  The
    run's "newest wave is ACTIVE" is therefore never a safe assumption for
    *any* worker's own wave identity -- this is the one lineage-aware
    resolution every non-dispatch call site (``record_progress``,
    ``terminate_worker``, ``remediate_node``) uses uniformly.
    """
    for event in store.read_events(root):
        if (event.get("event") == "gauntlet.worker.declared" and event.get("work_id") == work_id
                and event.get("run_id") == run_id and event.get("worker_id") == worker_id):
            wave_id = event.get("wave_id")
            if isinstance(wave_id, str) and wave_id:
                return wave_id
    _fail("ORCHESTRATOR-INVALID", "worker has no recorded declaration wave")


def _wave_would_complete(run: Mapping[str, Any], wave_id: str) -> bool:
    """Whether every one of ``wave_id``'s member nodes -- ``node_ids``, a
    real, required Store field set at wave declaration (B5 fix) -- now has a
    terminal lineage-head worker record.

    A member node with no worker record at all yet (never dispatched) is
    obviously not complete -- this alone is what closes B5's stranding bug,
    where a wave could reach ``COMPLETE`` while a declared-but-never-
    dispatched member could then never be declared into it.  A remediated
    node has two worker records; only its lineage HEAD -- the one no sibling
    worker of the same ``node_id`` names via ``remediates`` -- decides the
    node's own terminal state, never an earlier, superseded attempt.  ``run``
    must be the transaction's own in-flight candidate (already carrying this
    call's own worker's new state), so this stays race-free with the
    transition it decides alongside.
    """
    node_ids = run.get("waves", {}).get(wave_id, {}).get("node_ids")
    if not isinstance(node_ids, list) or not node_ids:
        return False
    for node_id in node_ids:
        head = _node_lineage_head(run, node_id)
        if head is None or head.get("state") not in TERMINAL_WORKER_STATES:
            return False
    return True


def record_progress(root: str | Path, work_id: str, run_id: str, worker_id: str,
                    admission: Mapping[str, str]) -> dict[str, Any]:
    """FASE-003 (FR-008(d), T017): record one progress transition correlated
    to a worker's active lease, renewing ``lease.expires_at`` to
    ``<record time> + LEASE_DURATION`` -- from now, not from the old expiry --
    so a worker producing genuine progress past its original lease window is
    never treated as expired solely because that window elapsed (FR-009,
    SC-010).  Requires the worker in ``PREPARED``; any other state has
    nothing live to renew.
    """
    identity = _validate_admission(admission)
    worker_id = _safe_name(worker_id, "worker")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    worker = run.get("workers", {}).get(worker_id)
    if not isinstance(worker, dict):
        _fail("WORKER-NOT-FOUND", "worker does not exist")
    if worker.get("state") != "PREPARED":
        _fail("WORKER-NOT-PREPARED", "worker is not in a progress-eligible state")
    lease = worker.get("lease")
    if not isinstance(lease, Mapping):
        _fail("LEASE-INVALID", "worker has no coordinator lease")
    wave_id = _worker_wave_id(root, work_id, run_id, worker_id)
    lease_id, fencing_token = lease.get("lease_id"), lease.get("fencing_token")
    recorded_at = datetime.now(timezone.utc).replace(microsecond=0)
    new_expires_at = (recorded_at + LEASE_DURATION).isoformat().replace("+00:00", "Z")

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
        if candidate.get("state") != "PREPARED":
            _fail("WORKER-NOT-PREPARED", "worker changed before progress could be recorded")
        candidate_lease = candidate.get("lease")
        if (not isinstance(candidate_lease, dict) or candidate_lease.get("lease_id") != lease_id
                or candidate_lease.get("fencing_token") != fencing_token):
            _fail("LEASE-INVALID", "worker lease changed before progress could be recorded")
        candidate_lease["expires_at"] = new_expires_at
        return document

    _transition_worker(
        root, work_id, run_id, identity, name=f"gauntlet-worker-progress-{run_id}-{worker_id}",
        event_name="gauntlet.worker.progress-recorded", worker_id=worker_id, lease=lease,
        mutate=mutate, wave_id=wave_id,
    )
    return {
        "verdict": "PROGRESS-RECORDED", "work_id": work_id, "run_id": run_id,
        "worker_id": worker_id, "expires_at": new_expires_at,
    }


def terminate_worker(root: str | Path, work_id: str, run_id: str, worker_id: str, outcome: str,
                     failure_class: str | None, admission: Mapping[str, str]) -> dict[str, Any]:
    """FASE-003 (FR-009/FR-010, ADR-0012, T018): terminate one ``PREPARED``
    worker.

    ``completed`` transitions ``PREPARED -> TERMINAL``; ``failed`` transitions
    ``PREPARED -> FAILED`` and requires ``failure_class`` from FR-010's closed
    set -- both edges already legal in ``store._validate_gauntlet_state_
    transitions``'s ``worker_edges`` table, just never driven by any command
    until now.  The classification is recorded as evidence on the transition
    itself: Store's event and receipt objects both have closed key sets with
    no spare slot for it, so it is encoded in the one free-form field that
    schema does leave open -- the immutable receipt's own ``name`` -- the
    same way every other transition in this file already bakes
    ``run_id``/``worker_id`` into its receipt name; ``run_projection``
    recovers it from there for ``gauntlet-status`` rather than trusting a
    caller-asserted flag on a later remediation call (FR-010).  Frees the
    worker's concurrent-cap slot (ADR-0012) regardless of outcome, since
    neither ``TERMINAL`` nor ``FAILED`` is in
    ``store.NON_TERMINAL_WORKER_STATES``.

    In the same transaction, if this is the last of the current wave's
    member nodes to reach a terminal state, the wave itself also transitions
    to ``COMPLETE`` -- see ``_wave_would_complete`` for the lineage-aware
    correctness rule this depends on.
    """
    if outcome == "completed":
        if failure_class is not None:
            _fail("INVALID-ARGUMENTS", "failure_class is only valid for a failed outcome")
        new_state = "TERMINAL"
    elif outcome == "failed":
        if failure_class not in FAILURE_CLASSES:
            _fail("FAILURE-CLASS-REQUIRED", "a failed outcome requires a valid --failure-class")
        new_state = "FAILED"
    else:
        _fail("INVALID-ARGUMENTS", "outcome must be completed or failed")

    identity = _validate_admission(admission)
    worker_id = _safe_name(worker_id, "worker")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    worker = run.get("workers", {}).get(worker_id)
    if not isinstance(worker, dict):
        _fail("WORKER-NOT-FOUND", "worker does not exist")
    if worker.get("state") != "PREPARED":
        _fail("WORKER-NOT-PREPARED", "worker is not in a terminable state")
    lease = worker.get("lease")
    if not isinstance(lease, Mapping):
        _fail("LEASE-INVALID", "worker has no coordinator lease")
    wave_id = _worker_wave_id(root, work_id, run_id, worker_id)
    receipt_name = (
        _failed_receipt_name(run_id, worker_id, failure_class) if new_state == "FAILED"
        else f"gauntlet-worker-terminal-{run_id}-{worker_id}"
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate_run = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        candidate_worker = candidate_run["workers"][worker_id]
        if candidate_worker.get("state") != "PREPARED":
            _fail("WORKER-NOT-PREPARED", "worker changed before it could be terminated")
        candidate_worker["state"] = new_state
        if _wave_would_complete(candidate_run, wave_id):
            candidate_run["waves"][wave_id]["state"] = "COMPLETE"
        return document

    _transition_worker(
        root, work_id, run_id, identity, name=receipt_name, event_name="gauntlet.worker.terminal",
        worker_id=worker_id, lease=lease, mutate=mutate, wave_id=wave_id,
    )
    result = {"verdict": "WORKER-TERMINAL", "work_id": work_id, "run_id": run_id, "worker_id": worker_id, "state": new_state}
    if new_state == "FAILED":
        result["failure_class"] = failure_class
    return result


def _mint_remediation_worker(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                             run: Mapping[str, Any], worker_id: str, node_id: str,
                             grant: Mapping[str, Any], wave_id: str, activation_max_workers: int) -> dict[str, Any]:
    """The shared budget-lineage scan and atomic mint (FR-007/FR-008(e),
    ADR-0015), reused verbatim by both remediation reasons.

    One Store transaction performs the shared per-node budget scan and the
    replacement worker's ``DECLARED`` mint together -- closing the TOCTOU gap
    a split lookup/mint design would leave open (plan.md Complexity
    Tracking).  The scan matches on ``node_id`` alone, never on which reason
    funded the sibling with a spent budget, so a node cannot chain
    remediation by alternating ``stall`` and ``transient-failure`` (FR-007:
    "not one budget per mechanism").  The subsequent
    ``PREPARING -> git worktree add -> PREPARED`` sequence is driven
    afterwards by ``prepare_worker``'s own existing intent protocol, exactly
    like first dispatch (``declare_worker``) already reuses it.

    FASE-003 (F2 fix, FR-005): "a stall-triggered replacement worker and a
    transient-failure retry each count against this same concurrent cap" --
    ``declare_wave`` is not the only mint path, so the cap check cannot live
    there alone.  ``activation_max_workers`` is the caller's own current
    activation-pinned cap (``gauntlet_remediate_command`` threads it down
    exactly the way ``gauntlet_wave_declare_command`` already threads it into
    ``declare_wave``); this function has no Execution DAG in hand (remediation
    never takes a ``--dag`` argument), so unlike ``declare_wave`` it cannot
    additionally intersect the DAG's own ``max_workers`` -- the activation cap
    is the only cap value available at a remediation mint, and enforcing it is
    what closes the reported gap (zero enforcement previously).  The check
    runs inside the same transaction as the budget-lineage scan and the STALL
    transition below, so it is race-free the same way they are.
    """
    sibling_count = sum(
        1 for candidate_worker_id, candidate_worker in run.get("workers", {}).items()
        if isinstance(candidate_worker, dict) and candidate_worker.get("node_id") == node_id
        and store.WORKER_REMEDIATION_SUFFIX_RE.fullmatch(candidate_worker_id)
    )
    new_worker_id = f"{node_id}-r{sibling_count + 1}"
    scopes = list(grant["scope_paths"])
    new_lease = _new_coordinator_lease(run_id, new_worker_id)
    new_lease["recovery_count"] = 1

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate_workers = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"]
        if any(
            isinstance(candidate, dict) and candidate.get("node_id") == node_id
            and isinstance(candidate.get("lease"), dict) and candidate["lease"].get("recovery_count") == 1
            for candidate in candidate_workers.values()
        ):
            _fail("REMEDIATION-BUDGET-SPENT", "node's remediation budget is already spent")
        if new_worker_id in candidate_workers:
            _fail("WORKER-CONFLICT", "remediation worker appeared during declaration")
        # FASE-003 (B2 fix): in the SAME transaction, transition the original
        # being replaced out of PREPARED -- a still-PREPARED original (the
        # stall path) would otherwise strand forever in PREPARED, permanently
        # occupying a non-terminal-cap slot (ADR-0012/FR-005) and permanently
        # blocking any dependent's readiness check (_node_lineage_head would
        # keep finding it as an ambiguous second "head" alongside the
        # replacement).  PREPARED -> STALLED is already a legal Store edge.
        # A FAILED original (the transient-failure path) is already terminal
        # and needs no further transition here.
        original = candidate_workers.get(worker_id)
        if isinstance(original, dict) and original.get("state") == "PREPARED":
            original["state"] = "STALLED"
        # FASE-003 (F2 fix, FR-005/ADR-0012): computed AFTER the original's
        # own STALLED transition above, so a freed slot is never
        # double-counted against the replacement about to be minted; the "+1"
        # accounts for that replacement itself, mirroring declare_wave's own
        # "non_terminal + len(requested) > effective_cap" shape.
        non_terminal = sum(
            1 for candidate in candidate_workers.values()
            if isinstance(candidate, dict) and candidate.get("state") in store.NON_TERMINAL_WORKER_STATES
        )
        if non_terminal + 1 > activation_max_workers:
            _fail("REMEDIATION-CAP-EXCEEDED", "remediation replacement would exceed the run's effective concurrent worker cap")
        candidate_workers[new_worker_id] = {
            "state": "DECLARED", "lease": copy.deepcopy(new_lease), "grant": None, "workspace": None,
            "node_id": node_id, "remediates": worker_id,
        }
        return document

    _transition_worker(
        root, work_id, run_id, admission, name=f"gauntlet-worker-declared-{run_id}-{new_worker_id}",
        event_name="gauntlet.worker.declared", worker_id=new_worker_id, lease=new_lease,
        mutate=mutate, wave_id=wave_id,
    )
    prepared = prepare_worker(
        root, work_id, run_id, new_worker_id, scopes, admission,
        node_id=node_id, remediates=worker_id, wave_id=wave_id,
    )
    return {
        "verdict": "REMEDIATION-RECORDED", "work_id": work_id, "run_id": run_id,
        "worker_id": new_worker_id, "remediates": worker_id, "recovery_count": 1,
        "worktree_key": prepared.get("worktree_key"), "base_commit": prepared.get("base_commit"),
    }


def remediate_node(root: str | Path, work_id: str, run_id: str, worker_id: str, reason: str,
                   admission: Mapping[str, str], *, stall_minutes: int, activation_max_workers: int) -> dict[str, Any]:
    """FASE-003 (FR-007/FR-009/FR-010, ADR-0015, T019/T023): remediate one
    node's current worker.

    Both remediation reasons -- ``"stall"`` (User Story 3, T019) and
    ``"transient-failure"`` (User Story 4, T023) -- share the exact same
    budget-lineage scan and atomic mint (:func:`_mint_remediation_worker`);
    only each reason's own eligibility precondition differs:

    * ``"stall"`` requires the worker still ``PREPARED``, and is verified
      from the worker's own recorded lease-activity timestamp against the
      configured stall window -- never caller-asserted.
    * ``"transient-failure"`` requires the worker already ``FAILED`` (via
      ``gauntlet-worker-terminal``) with a classification recorded in
      FR-010's closed transient set, read back from the coordinator's own
      immutable evidence (``_read_worker_failure_class``) rather than a bare
      flag on this call -- the core function does not trust a caller-passed
      classification any more than it trusts a caller-asserted stall.

    ``stall_minutes`` is the activation-pinned ``limits.stall_minutes`` value
    (FASE-001), threaded in by the caller exactly like ``declare_wave``'s
    ``activation_max_workers``.  ``activation_max_workers`` (F2 fix, FR-005)
    is that same value -- ``gauntlet_remediate_command`` threads it down
    exactly the way ``gauntlet_wave_declare_command`` already threads it into
    ``declare_wave``: "a stall-triggered replacement worker and a transient-
    failure retry each count against this same concurrent cap" (FR-005).
    This module never reads config content itself; both values are required
    and validated even for a ``transient-failure`` call so the CLI adapter's
    calling convention stays uniform across both reasons.
    """
    if reason not in {"stall", "transient-failure"}:
        _fail("REMEDIATION-REASON-UNSUPPORTED", f"remediation reason is not recognized: {reason}")
    if type(stall_minutes) is not int or stall_minutes < 1:
        _fail("INVALID-ARGUMENTS", "stall window is invalid")
    if type(activation_max_workers) is not int or activation_max_workers < 1:
        _fail("INVALID-ARGUMENTS", "activation worker cap is invalid")

    identity = _validate_admission(admission)
    worker_id = _safe_name(worker_id, "worker")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    worker = run.get("workers", {}).get(worker_id)
    if not isinstance(worker, dict):
        _fail("WORKER-NOT-FOUND", "worker does not exist")

    if reason == "stall":
        if worker.get("state") != "PREPARED":
            _fail("WORKER-NOT-PREPARED", "worker is not in a remediation-eligible state")
        lease = worker.get("lease")
        if not isinstance(lease, Mapping):
            _fail("LEASE-INVALID", "worker has no coordinator lease")
        if datetime.now(timezone.utc) - _last_activity_at(lease) < timedelta(minutes=stall_minutes):
            _fail("STALL-NOT-ELIGIBLE", "worker has recorded progress within the configured stall window")
    else:
        if worker.get("state") != "FAILED":
            _fail("WORKER-NOT-FAILED", "worker is not in a transient-failure-eligible state")
        # Defensive, not merely a re-check of what ``gauntlet-worker-terminal``
        # already enforced (FR-010): the core function does not trust its
        # caller, so it re-derives the classification from the coordinator's
        # own immutable evidence and re-validates it against the exact same
        # closed set, rather than trusting "state == FAILED" alone.
        failure_class = _read_worker_failure_class(root, work_id, run_id, run, worker_id, worker)
        if failure_class not in FAILURE_CLASSES:
            _fail("FAILURE-CLASS-NOT-TRANSIENT", "worker failure is not classified as transient")

    node_id = worker.get("node_id")
    grant = worker.get("grant")
    if not isinstance(grant, Mapping):
        _fail("LEASE-INVALID", "worker has no coordinator grant")
    # Resolved by the worker's own journal-recorded declaration, never by
    # assuming "the run's newest wave is ACTIVE" (B1 fix -- that assumption
    # is false the moment a worker's own wave has already gone COMPLETE):
    # a FAILED worker's own wave may already be COMPLETE (terminating a
    # wave's last non-terminal node can complete the wave in the very same
    # transaction as the failure now being remediated), and a still-PREPARED
    # worker's own wave is provably still this same value either way -- see
    # ``_worker_wave_id``'s docstring.
    wave_id = _worker_wave_id(root, work_id, run_id, worker_id)

    return _mint_remediation_worker(
        root, work_id, run_id, identity, run, worker_id, node_id, grant, wave_id, activation_max_workers,
    )


def cleanup_worker(root: str | Path, work_id: str, run_id: str, worker_id: str,
                   admission: Mapping[str, str]) -> dict[str, Any]:
    """Remove only a recorded, terminal, clean, converged exact worktree."""
    identity = _validate_admission(admission); worker_id = _safe_name(worker_id, "worker")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    # ADR-0023: every receipt/event this call mints from here on must anchor
    # to the run's own recorded admission, never the freshly re-derived live
    # one -- gauntlet-converge advances HEAD on purpose, so live base_commit
    # legitimately diverges from the run's admission after any convergence.
    identity = run["admission"]
    worker = run.get("workers", {}).get(worker_id)
    if not isinstance(worker, dict): _fail("WORKER-NOT-FOUND", "worker does not exist")
    workspace = worker.get("workspace")
    if not isinstance(workspace, dict): return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    target, expected = _workspace_identity(root, work_id, run_id, worker_id, identity)
    lease = worker.get("lease")
    if not _same_workspace_identity(workspace, expected):
        return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    if worker.get("state") == "CLEANED":
        return {"verdict": "REUSED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    predicates = worker.get("state") == "TERMINAL" and all(workspace.get(key) is True for key in ("clean", "converged", "cleanup_eligible"))
    if worker.get("state") != "CLEANING" and not predicates:
        return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    git_state = _workspace_git_state(root, target, expected)
    if worker.get("state") == "CLEANING" and _workspace_target_absent(root, target, workspace):
        pass
    elif git_state != "EXACT":
        return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    elif not _exact_worktree_is_clean(root, target):
        # ``workspace.clean`` is a coordinator-recorded predicate, but it is
        # not a substitute for checking the exact Git worktree immediately
        # before we make a destructive intent visible.
        return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    if worker.get("state") == "TERMINAL":
        def cleaning(document: dict[str, Any]) -> dict[str, Any]:
            candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            if candidate.get("state") != "TERMINAL": _fail("WORKER-CONFLICT", "worker changed before cleanup")
            candidate["state"] = "CLEANING"; return document
        if not isinstance(lease, Mapping): _fail("LEASE-INVALID", "worker has no coordinator lease")
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-cleaning-{run_id}-{worker_id}", event_name="gauntlet.worker.cleaning", worker_id=worker_id, lease=lease, mutate=cleaning)
        if _workspace_git_state(root, target, expected) != "EXACT":
            return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
    if _workspace_git_state(root, target, expected) == "EXACT":
        if not _exact_worktree_is_clean(root, target):
            return {"verdict": "PRESERVED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}
        removed = _git(root, "worktree", "remove", str(target))
        if removed.returncode != 0: _fail("WORKTREE-REMOVE-FAILED", "could not remove exact worker worktree")
    if not _workspace_target_absent(root, target, workspace):
        _fail("WORKSPACE-PRESERVED", "worker worktree removal did not converge")
    def cleaned(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
        if candidate.get("state") != "CLEANING": _fail("WORKER-CONFLICT", "worker changed before cleanup finalization")
        candidate["state"] = "CLEANED"; return document
    if not isinstance(lease, Mapping): _fail("LEASE-INVALID", "worker has no coordinator lease")
    _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-cleaned-{run_id}-{worker_id}", event_name="gauntlet.worker.cleaned", worker_id=worker_id, lease=lease, mutate=cleaned)
    return {"verdict": "CLEANED", "work_id": work_id, "run_id": run_id, "worker_id": worker_id}


# FASE-004 (FR-001-FR-005, FR-010, ADR-0020/0021/0022): serial convergence of
# one wave's successful workers into the work item's execution branch.  Every
# merge is its own Store transaction, so a later conflict never unwinds an
# earlier sibling's integration; no conflict is ever resolved automatically
# and nothing here ever touches a Git remote.


def _head_commit(root: str | Path) -> str:
    process = _git(root, "rev-parse", "HEAD")
    head = process.stdout.strip()
    if process.returncode != 0 or not _hex40(head):
        _fail("BASE-COMMIT-UNAVAILABLE", "execution branch head is unavailable")
    return head


def _branch_head(root: str | Path, branch: str) -> str:
    process = _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
    head = process.stdout.strip()
    if process.returncode != 0 or not _hex40(head):
        _fail("WORKSPACE-PRESERVED", f"declared worker branch is unavailable: {branch}")
    return head


def _branch_changed_paths(root: str | Path, branch: str) -> set[str]:
    """Every repo-relative path this branch changes since it diverged."""
    base = _git(root, "merge-base", "HEAD", branch)
    if base.returncode != 0 or not _hex40(base.stdout.strip()):
        _fail("WORKSPACE-PRESERVED", f"declared worker branch has no merge base: {branch}")
    changed = _git(root, "diff", "--name-only", f"{base.stdout.strip()}..{branch}")
    if changed.returncode != 0:
        _fail("WORKSPACE-PRESERVED", f"declared worker branch is unreadable: {branch}")
    return {line for line in changed.stdout.splitlines() if line}


def _converged_lineage_head(run: Mapping[str, Any], node_id: str) -> bool:
    """Whether ``node_id``'s lineage head is the success outcome *and* is
    already integrated.  ``FAILED``/``STALLED``/``ORPHANED``/``CONFLICT`` are
    terminal but never merged, so they never satisfy this."""
    entry = _node_lineage_head_entry(run, node_id)
    if entry is None or entry[1].get("state") != "TERMINAL":
        return False
    workspace = entry[1].get("workspace")
    return isinstance(workspace, Mapping) and workspace.get("converged") is True


def _all_converged(run: Mapping[str, Any], node_ids: Any) -> bool:
    if not isinstance(node_ids, list) or not node_ids:
        return False
    return all(_converged_lineage_head(run, node_id) for node_id in node_ids)


def _conflict_record(reason: str, node_ids: list[str], execution_branch_head: str,
                     worker_heads: Mapping[str, str]) -> dict[str, Any]:
    """FR-002/FR-003's single four-key shape, always fully populated -- never
    a subset conditioned on the reason."""
    return {
        "node_ids": sorted(node_ids), "reason": reason,
        "execution_branch_head": execution_branch_head, "worker_heads": dict(worker_heads),
    }


def _record_conflict(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                     wave_id: str, wave: Mapping[str, Any], conflict: Mapping[str, Any]) -> None:
    """Persist the wave's open block, unless the identical one already is.

    Re-blocking on unchanged fingerprints is a pure read: minting the same
    semantic event twice is what ``_recover_pending_transition_locked``
    already rejects as divergence.
    """
    if wave.get("last_conflict") == conflict:
        return
    receipt, event = _receipt_and_event(
        name=f"gauntlet-converge-conflict-{run_id}-{wave_id}", event_name="gauntlet.converge.conflict",
        work_id=work_id, run_id=run_id, admission=admission, wave_id=wave_id,
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["waves"][wave_id]
        candidate["last_conflict"] = copy.deepcopy(dict(conflict))
        return document

    store.transact_with_event(root, mutate, event=event, receipt=receipt)


def _merge_worker_branch(root: str | Path, branch: str, head: str) -> bool:
    """Integrate one worker branch, or leave the tree exactly as it was.

    A branch with no commits beyond what the execution branch already
    contains is a trivial success, not an error and not a conflict.
    """
    before = _head_commit(root)
    if _git(root, "merge-base", "--is-ancestor", head, before).returncode == 0:
        return True
    merged = _git(root, "merge", "--no-ff", "--no-edit", "-m", f"gauntlet: integrate {branch}", branch)
    if merged.returncode == 0:
        return True
    _git(root, "merge", "--abort")
    if _head_commit(root) != before:
        _git(root, "reset", "--hard", before)
    if _head_commit(root) != before:
        _fail("WORKSPACE-PRESERVED", "failed integration attempt could not be reverted")
    return False


def _mint_worker_converged(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                           wave_id: str, worker_id: str, worker: Mapping[str, Any]) -> None:
    lease = worker.get("lease")
    if not isinstance(lease, Mapping):
        _fail("LEASE-INVALID", "worker has no coordinator lease")

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate_run = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        candidate_worker = candidate_run["workers"][worker_id]
        if candidate_worker.get("state") != "TERMINAL":
            _fail("WORKER-CONFLICT", "worker changed before convergence could be recorded")
        candidate_worker["workspace"]["converged"] = True
        # Absence is the "resolved" signal (FR-011): a member that merges
        # after a block clears it in the very transaction that proves it.
        candidate_run["waves"][wave_id].pop("last_conflict", None)
        return document

    _transition_worker(
        root, work_id, run_id, admission, name=f"gauntlet-worker-converged-{run_id}-{worker_id}",
        event_name="gauntlet.converge.worker-converged", worker_id=worker_id, lease=lease,
        mutate=mutate, wave_id=wave_id,
    )


def _mint_wave_converged(root: str | Path, work_id: str, run_id: str,
                         admission: Mapping[str, str], wave_id: str) -> dict[str, Any]:
    receipt, event = _receipt_and_event(
        name=f"gauntlet-wave-converged-{run_id}-{wave_id}", event_name="gauntlet.converge.wave-converged",
        work_id=work_id, run_id=run_id, admission=admission, wave_id=wave_id,
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["waves"][wave_id]
        candidate["converged"] = True
        candidate.pop("last_conflict", None)
        return document

    store.transact_with_event(root, mutate, event=event, receipt=receipt)
    return _read_runs(root, work_id)[run_id]


def _mint_run_completed(root: str | Path, work_id: str, run_id: str,
                        admission: Mapping[str, str], run: Mapping[str, Any]) -> dict[str, Any]:
    receipt, event = _receipt_and_event(
        name=f"gauntlet-run-completed-{run_id}", event_name="gauntlet.run.completed",
        work_id=work_id, run_id=run_id, admission=admission, wave_id=max(run["waves"]),
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        if candidate.get("state") in {"BLOCKED", "COMPLETE"}:
            _fail("RUN-NOT-ELIGIBLE", "run became terminal before completion could be recorded")
        candidate["state"] = "COMPLETE"
        return document

    store.transact_with_event(root, mutate, event=event, receipt=receipt)
    return _read_runs(root, work_id)[run_id]


def _close_convergence_chain(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                             run: dict[str, Any], wave_id: str,
                             nodes_by_id: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    """Mint whichever of the two closing transitions the current state earns.

    ``transact_with_event`` mints exactly one event per transaction, so the
    wave's last ``worker-converged``, the wave's own flag, and the run's
    ``COMPLETE`` are up to three sequential transactions -- an interruption
    between any two of them is real, and this same function closes the gap
    on the next call because convergence runs it unconditionally.  The run's
    predicate is the *pinned DAG's* whole node set, never a wave count: a
    run almost always needs further waves after the first one converges.
    """
    wave = run.get("waves", {}).get(wave_id)
    if isinstance(wave, dict) and wave.get("converged") is not True and _all_converged(run, wave.get("node_ids")):
        run = _mint_wave_converged(root, work_id, run_id, admission, wave_id)
    if run.get("state") not in {"BLOCKED", "COMPLETE"} and _all_converged(run, sorted(nodes_by_id)):
        run = _mint_run_completed(root, work_id, run_id, admission, run)
    return run


def converge_wave(root: str | Path, work_id: str, run_id: str, dag_path: Any, wave_id: str,
                  admission: Mapping[str, str], *, execution_branch: Any,
                  agent_execute_floor: str, markdown_floor: str) -> dict[str, Any]:
    """Integrate one wave's successful workers into ``execution_branch``.

    The checks run in a fixed order that is itself part of the contract:
    admission identity, the run's DAG pin, the terminal-run shortcut and its
    reconciliation, execution-branch/worktree state, wave order, and only
    then the scope pre-pass and the merges themselves.  The pin is
    revalidated before the terminal-run check on purpose -- FR-004c admits no
    exception for a replay, and a ``COMPLETE`` run always has a pin by
    construction, so a stale ``--dag`` can never report success against the
    wrong DAG.

    ``execution_branch`` is the work item's recorded binding, resolved by the
    CLI adapter from the same ``development`` block ``checkpoint``/
    ``phase-turn`` already read -- the same way ``activation_max_workers``
    crosses this boundary.  The live checkout is compared against it here so
    the fixed order above holds for both halves of that pairing.
    """
    identity = _validate_admission(admission)
    _require_base_commit(root, identity)
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        _fail("RUN-NOT-FOUND", "run identifier is invalid")
    wave_id = _safe_name(wave_id, "wave")
    _, nodes_by_id, dag_content_sha256 = _load_and_validate_dag(
        root, dag_path, agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
    )
    store.recover_pending_transition(root)
    run = _read_runs(root, work_id).get(run_id)
    if not isinstance(run, dict):
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    # Convergence is the one primitive whose own successful merges advance
    # the coordinator's HEAD, so the run's recorded ``base_commit`` stops
    # equalling the live one from its first integration onward.  Comparing it
    # would make a wave's second member unconvergeable by construction, and
    # the Store forbids the alternative anyway: ``_candidate_transition``
    # requires every event's ``base_commit`` to be the run's *recorded* one.
    # The four identity digests FR-012 actually protects are still compared
    # in full, and the current activation was proved by the CLI boundary.
    recorded = run.get("admission")
    if not isinstance(recorded, Mapping) or any(recorded.get(key) != identity[key] for key in _ADMISSION_IDENTITY_KEYS):
        _fail("IDENTITY-STALE", "current activation differs from run admission")
    identity = _validate_admission(recorded)
    _require_dag_pin(run, dag_content_sha256)

    if run.get("state") == "BLOCKED":
        _fail("RUN-NOT-ELIGIBLE", "run was abandoned and accepts no further transition")
    if run.get("state") == "COMPLETE":
        if wave_id != max(run["waves"]):
            _fail("RUN-NOT-ELIGIBLE", "a complete run replays only the wave that closed it")
        return _wave_converged_reuse(work_id, run_id, wave_id)
    run = _close_convergence_chain(root, work_id, run_id, identity, run, max(run["waves"]), nodes_by_id)

    if not isinstance(execution_branch, str) or not execution_branch:
        _fail("EXECUTION-BRANCH-UNSET", "work item has no bound execution branch")
    live = _git(root, "branch", "--show-current")
    if live.returncode != 0:
        _fail("GIT-UNAVAILABLE", "could not read the current execution branch")
    if live.stdout.strip() != execution_branch:
        _fail("EXECUTION-BRANCH-MISMATCH", f"work item is bound to {execution_branch}")
    entries = _porcelain_entries(root)
    if entries is None:
        _fail("EXECUTION-TREE-DIRTY", "coordinator worktree status is unavailable")
    untracked = _untracked_paths(entries)
    if not _exact_worktree_is_clean(root, Path(root), include_untracked=False):
        _fail("EXECUTION-TREE-DIRTY", "coordinator worktree carries uncommitted tracked changes")

    waves = run.get("waves", {})
    wave = waves.get(wave_id)
    if not isinstance(wave, dict):
        _fail("WAVE-NOT-FOUND", "requested wave does not exist in this run")
    if wave.get("converged") is True:
        return _wave_converged_reuse(work_id, run_id, wave_id)
    pending = next((candidate for candidate in sorted(waves) if waves[candidate].get("converged") is not True), None)
    if wave_id != pending:
        _fail("WAVE-CONVERGENCE-OUT-OF-ORDER", "an earlier wave is not fully converged")
    if wave.get("state") != "COMPLETE":
        _fail("WAVE-CONVERGENCE-OUT-OF-ORDER", "wave still has a member that has not reached a terminal state")

    members = wave.get("node_ids") or []
    unknown = [node_id for node_id in members if node_id not in nodes_by_id]
    if unknown:
        _fail("WAVE-NODE-UNKNOWN", f"wave names a node the pinned Execution DAG does not declare: {unknown[0]}")
    mergeable: list[tuple[str, str, Mapping[str, Any]]] = []
    for node_id in sorted(members):
        entry = _node_lineage_head_entry(run, node_id)
        if entry is None or entry[1].get("state") != "TERMINAL" or not isinstance(entry[1].get("workspace"), Mapping):
            continue
        mergeable.append((node_id, entry[0], entry[1]))
    branch_heads = {
        node_id: _branch_head(root, worker["workspace"]["branch"]) for node_id, _, worker in mergeable
    }

    overlapping = _overlapping_scope(nodes_by_id, [node_id for node_id, _, _ in mergeable])
    if overlapping:
        _record_conflict(
            root, work_id, run_id, identity, wave_id, wave,
            _conflict_record("scope-overlap", overlapping, _head_commit(root),
                             {node_id: branch_heads[node_id] for node_id in overlapping}),
        )
        _fail("INTEGRATION_CONFLICT", f"wave members declare overlapping files: {', '.join(overlapping)}")

    collisions: set[str] = set()
    changed_by_node: dict[str, set[str]] = {}
    for node_id, _, worker in mergeable:
        changed_by_node[node_id] = _branch_changed_paths(root, worker["workspace"]["branch"])
        collisions |= changed_by_node[node_id] & untracked
    if collisions:
        _fail("EXECUTION-TREE-DIRTY", f"untracked paths would be overwritten: {', '.join(sorted(collisions))}")

    # The grant is only a fence if something checks it against what the branch
    # actually changed. Until this pass existed, `_overlapping_scope` compared
    # DECLARED files against each other and nothing ever compared a worker's
    # diff to its own grant -- so a worker could edit tasks.md, or another
    # node's files, and the merge would take it. Refuse before the first merge,
    # so a wave never integrates half of a violating set.
    for node_id, _, worker in mergeable:
        if worker["workspace"].get("converged") is True:
            continue
        granted = set(worker.get("grant", {}).get("scope_paths") or [])
        outside = sorted(changed_by_node[node_id] - granted)
        if outside:
            _fail("GRANT-SCOPE-VIOLATION",
                  f"worker wrote outside its grant: {node_id} -> {', '.join(outside[:5])}")

    converged: list[str] = []
    for node_id, worker_id, worker in mergeable:
        if worker["workspace"].get("converged") is True:
            continue
        candidate = _conflict_record(
            "content-conflict", [node_id], _head_commit(root), {node_id: branch_heads[node_id]},
        )
        if wave.get("last_conflict") == candidate:
            _fail("INTEGRATION_CONFLICT", f"integration is still blocked on {node_id}")
        if not _merge_worker_branch(root, worker["workspace"]["branch"], branch_heads[node_id]):
            _record_conflict(root, work_id, run_id, identity, wave_id, wave, candidate)
            _fail("INTEGRATION_CONFLICT", f"worker branch does not merge cleanly: {node_id}")
        _mint_worker_converged(root, work_id, run_id, identity, wave_id, worker_id, worker)
        converged.append(node_id)
        run = _read_runs(root, work_id)[run_id]
        wave = run["waves"][wave_id]

    run = _close_convergence_chain(root, work_id, run_id, identity, run, wave_id, nodes_by_id)
    return {
        "verdict": "WAVE-CONVERGED", "work_id": work_id, "run_id": run_id, "wave_id": wave_id,
        "converged": converged, "wave_converged": run["waves"][wave_id].get("converged") is True,
        "run_state": run.get("state"),
    }


def _wave_converged_reuse(work_id: str, run_id: str, wave_id: str) -> dict[str, Any]:
    return {"verdict": "WAVE-CONVERGED-REUSED", "work_id": work_id, "run_id": run_id, "wave_id": wave_id}


# FASE-004 (FR-007, FR-008, FR-014, ADR-0020): the run's terminal lifecycle
# seen from the outside -- the exhaustive enumeration ``checkpoint --step
# ship`` scans, and the single human act that makes an irrecoverable run
# terminal.  Neither ever touches a Git remote (FR-009).


def list_run_states(root: str | Path, work_id: str) -> list[dict[str, Any]]:
    """Every admitted run's identifier and state, for the ship gate (FR-007).

    Deliberately not :func:`run_projection`, which returns exactly one run --
    "the run most recent by ``run_id``" is a lexicographic max over an
    admission hash, not a chronological choice, so a stale-but-incomplete run
    would be silently skipped: fail-open, the opposite of this gate's purpose.

    Two layers, the same pair :func:`run_projection` already needs:
    ``store_exists`` first, because ``_read_runs``' own ``absent_ok`` covers
    only a work item missing from an *existing* snapshot, never a Store that
    was never initialised -- the very case FR-008's no-op (a V2 or
    never-admitted work item) must not trip on.  ``store_exists`` is
    lstat-based, so a dangling symlink is not read as a plain absence.
    """
    if not store.store_exists(root):
        return []
    runs = _read_runs(root, work_id, absent_ok=True)
    return [{"run_id": run_id, "state": runs[run_id].get("state")} for run_id in sorted(runs)]


def abandon_run(root: str | Path, work_id: str, run_id: str,
                authorization: Mapping[str, Any]) -> dict[str, Any]:
    """Mark one irrecoverable run ``BLOCKED`` on explicit human authorization.

    This is the only mutating primitive in this module that does **not** prove
    the current activation, and the deviation is the whole reason it exists
    (FR-014, ADR-0020): it derives ``base_commit`` and identity from the
    target run's own recorded ``admission``, never from the live one, and
    never runs ``_require_base_commit`` over that derived value.  A run stale
    enough to need abandoning belongs, by definition, to an older generation
    than the one currently active, and its original commit may already be
    unreachable in Git -- requiring current identity would make this command
    useless in exactly the case FR-007's deadlock needs it for.

    The bundle's own ``human-authorization/v1`` form is validated at the CLI
    boundary by ``attestation._validate_human_authorization``; this module
    imports only ``store`` and records the bundle verbatim, so ``authorized_
    by``/``receipt_ref`` stay recoverable -- a bare digest would prove only
    that some bundle once existed.  ``BLOCKED`` is absorbing, so the Store's
    write-once guard on ``abandon_authorization`` is structural here rather
    than a policy choice: a resubmission either replays the identical bundle
    or is refused.
    """
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        _fail("RUN-NOT-FOUND", "run identifier is invalid")
    if not isinstance(authorization, Mapping) or not authorization:
        _fail("ABANDON-AUTHORIZATION-INVALID", "run abandonment requires a human authorization bundle")
    bundle = copy.deepcopy(dict(authorization))
    store.recover_pending_transition(root)
    run = _read_runs(root, work_id).get(run_id)
    if not isinstance(run, dict):
        _fail("RUN-NOT-FOUND", "requested durable run does not exist")
    identity = _validate_admission(run.get("admission"))
    if run.get("state") == "BLOCKED":
        if run.get("abandon_authorization") != bundle:
            _fail("RUN-NOT-ELIGIBLE", "run was already abandoned under a different authorization")
        return {"verdict": "RUN-ABANDON-REUSED", "work_id": work_id, "run_id": run_id, "state": "BLOCKED"}
    if run.get("state") == "COMPLETE":
        _fail("RUN-NOT-ELIGIBLE", "a complete run has no work left to abandon")

    receipt, event = _receipt_and_event(
        name=f"gauntlet-run-abandoned-{run_id}", event_name="gauntlet.run.abandoned",
        work_id=work_id, run_id=run_id, admission=identity, wave_id=max(run["waves"]),
    )

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        if candidate.get("state") in {"BLOCKED", "COMPLETE"}:
            _fail("RUN-NOT-ELIGIBLE", "run became terminal before abandonment could be recorded")
        candidate["state"] = "BLOCKED"
        candidate["abandon_authorization"] = copy.deepcopy(bundle)
        return document

    store.transact_with_event(root, mutate, event=event, receipt=receipt)
    return {"verdict": "RUN-ABANDONED", "work_id": work_id, "run_id": run_id, "state": "BLOCKED"}


# The public adapter keeps the shorter names.  Retain the explicit internal
# names above because they make the one-time and read-only boundaries obvious
# to future coordinator code.
def admit_or_reuse(root: str | Path, work_id: str, activation: Mapping[str, str]) -> dict[str, Any]:
    return admit_or_reuse_run(root, work_id, activation)


def project_run(root: str | Path, work_id: str, run_id: str | None = None) -> dict[str, Any] | None:
    return run_projection(root, work_id, run_id)


def record_resume(root: str | Path, work_id: str, run_id: str,
                  activation: Mapping[str, str]) -> dict[str, Any]:
    return record_resume_decision(root, work_id, run_id, activation)
