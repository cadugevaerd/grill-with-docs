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
                       admission: Mapping[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = {
        "category": "runtime", "name": name, "work_id": work_id,
        "run_id": run_id, "wave_id": WAVE_ID,
        "base_commit": admission["base_commit"],
        "input_sha256": _input_hash(admission), "output_sha256": None,
    }
    # Store binds and verifies this value against the exact durable payload.
    payload = {"category": receipt["category"], "name": receipt["name"], **{
        key: receipt[key] for key in ("work_id", "run_id", "wave_id", "base_commit", "input_sha256", "output_sha256")
    }}
    event = {
        "event": event_name, "work_id": work_id, "run_id": run_id,
        "wave_id": WAVE_ID, "base_commit": admission["base_commit"],
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
            "waves": {WAVE_ID: {"state": "DECLARED"}}, "workers": {},
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
        })
    return {
        "run_id": run_id, "state": run.get("state"), "recovery_count": run.get("recovery_count"),
        "base_commit": run.get("admission", {}).get("base_commit"), "workers": workers,
        "last_transition": _project_last_transition(root, work_id, run_id, run),
    }


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


def _exact_worktree_is_clean(root: str | Path, target: Path) -> bool:
    """Prove the registered linked worktree has no tracked or untracked dirt."""
    status = _git(target, "status", "--porcelain")
    if status.returncode != 0:
        return False
    return not status.stdout.strip()


def _worker_receipt_event(name: str, event_name: str, work_id: str, run_id: str,
                          admission: Mapping[str, str], worker_id: str,
                          lease: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build worker-scoped evidence bound to the coordinator lease fence."""
    receipt, event = _receipt_and_event(name=name, event_name=event_name, work_id=work_id,
                                        run_id=run_id, admission=admission)
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
    if run.get("admission") != identity:
        _fail("IDENTITY-STALE", "current activation differs from run admission")
    if run.get("state") in {"BLOCKED", "COMPLETE"}:
        _fail("RUN-NOT-ELIGIBLE", "run is not eligible for worker preparation")
    return run


def _transition_worker(root: str | Path, work_id: str, run_id: str, admission: Mapping[str, str],
                       *, name: str, event_name: str, worker_id: str,
                       lease: Mapping[str, Any], mutate: Any) -> None:
    receipt, event = _worker_receipt_event(name, event_name, work_id, run_id, admission, worker_id, lease)
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
        "expires_at": (started + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "state": "ACTIVE", "recovery_count": 0,
    }


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
                   scope_paths: Any, admission: Mapping[str, str]) -> dict[str, Any]:
    """Persist a worktree intent, make exactly that Git worktree, then finalize.

    This deliberately contains no dispatch or process launch.  An interrupted
    intent is reconciled only when all three Git identities (path, branch,
    base) are exact; anything partial is retained as ORPHANED.
    """
    identity = _validate_admission(admission)
    worker_id = _safe_name(worker_id, "worker")
    scopes = _strict_scopes(scope_paths)
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
    target, expected_workspace = _workspace_identity(root, work_id, run_id, worker_id, identity)
    existing = run.get("workers", {}).get(worker_id)
    if existing is not None and not isinstance(existing, dict):
        _fail("WORKER-INVALID", "worker record is invalid")
    if isinstance(existing, dict):
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
        def declare(document: dict[str, Any]) -> dict[str, Any]:
            candidate = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
            if worker_id in candidate["workers"]:
                _fail("WORKER-CONFLICT", "worker appeared during declaration")
            candidate["workers"][worker_id] = {"state": "DECLARED", "lease": copy.deepcopy(lease), "grant": None, "workspace": None}
            return document
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-declared-{run_id}-{worker_id}", event_name="gauntlet.worker.declared", worker_id=worker_id, lease=lease, mutate=declare)

    # Declare the intent separately so no Store snapshot can claim a Git
    # effect before it exists.
    current = _run_for_worker(root, work_id, run_id, identity)["workers"][worker_id]
    current_lease = current.get("lease")
    if not isinstance(current_lease, Mapping):
        # Reconcile an older interrupted PREPARING intent by first recording
        # the coordinator lease it lacked.  The repair itself is worker-scoped
        # evidence, so every subsequent Git effect has a durable fence.
        repaired_lease = _new_coordinator_lease(run_id, worker_id)
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
                           lease=repaired_lease, mutate=establish_lease)
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
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-preparing-{run_id}-{worker_id}", event_name="gauntlet.worker.preparing", worker_id=worker_id, lease=current_lease, mutate=preparing)
    elif current["state"] != "PREPARING":
        _fail("WORKER-CONFLICT", "worker is not preparable")

    state = _workspace_git_state(root, target, expected_workspace)
    if state == "DIVERGENT":
        def orphan(document: dict[str, Any]) -> dict[str, Any]:
            worker = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            if worker.get("state") != "PREPARING": _fail("WORKER-CONFLICT", "worker changed during reconciliation")
            worker["state"] = "ORPHANED"; return document
        _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-orphaned-{run_id}-{worker_id}", event_name="gauntlet.worker.orphaned", worker_id=worker_id, lease=current_lease, mutate=orphan)
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
    _transition_worker(root, work_id, run_id, identity, name=f"gauntlet-worker-prepared-{run_id}-{worker_id}", event_name="gauntlet.worker.prepared", worker_id=worker_id, lease=current_lease, mutate=prepared)
    return _prepared_response(work_id, run_id, worker_id, expected_workspace)


def cleanup_worker(root: str | Path, work_id: str, run_id: str, worker_id: str,
                   admission: Mapping[str, str]) -> dict[str, Any]:
    """Remove only a recorded, terminal, clean, converged exact worktree."""
    identity = _validate_admission(admission); worker_id = _safe_name(worker_id, "worker")
    store.recover_pending_transition(root)
    run = _run_for_worker(root, work_id, run_id, identity)
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
