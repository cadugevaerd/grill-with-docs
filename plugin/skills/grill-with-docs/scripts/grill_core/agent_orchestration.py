"""Closed, durable portion of the agent-orchestration v1 contract.

This module is deliberately pure: the Store owns locking and durable writes.
Keeping validation here lets every Store path (CAS, transaction and WAL
recovery) apply the same rules instead of relying on CLI callers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

SCHEMA = "grill-agent-orchestration/v1"
EVENT_SCHEMA = "grill-orchestration-event/v1"
CHECKPOINT_SCHEMA = "grill-continuity-checkpoint/v1"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONTEXT_STATES = {"PREPARED", "ACTIVE", "QUIESCING", "RELEASED", "SUPERSEDED"}
_OPERATION_STATES = {"INTENT", "APPLIED", "CONFIRMED", "UNKNOWN", "REFUSED"}


class OrchestrationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise OrchestrationError(message)


def _digest(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(f"invalid {label}")


def _id(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail(f"invalid {label}")


def _safe_path(value: Any) -> None:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        _fail("invalid scope file")
    parts = value.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        _fail("invalid scope file")


def _object(value: Any, required: set[str], optional: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not required.issubset(value) or set(value) - required - optional:
        _fail(f"invalid {label} keys")
    return value


def _context(context_id: str, value: Any) -> None:
    _id(context_id, "context id")
    required = {"context_id", "epoch", "predecessor_context_id", "continuity_ref", "runtime", "adapter", "activation", "campaign", "scheduler_runs", "leader", "state", "policy_sha256", "inputs_sha256"}
    optional = {"worktree_identity", "presentation"}
    value = _object(value, required, optional, "context")
    if value["context_id"] != context_id or type(value["epoch"]) is not int or value["epoch"] <= 0:
        _fail("invalid context identity")
    if value["state"] not in _CONTEXT_STATES:
        _fail("invalid context state")
    for key in ("policy_sha256", "inputs_sha256"):
        _digest(value[key], key)
    if not isinstance(value["runtime"], str) or value["runtime"] not in {"codex", "claude"} or not isinstance(value["adapter"], str) or not value["adapter"]:
        _fail("invalid context runtime")
    if not isinstance(value["scheduler_runs"], dict) or not isinstance(value["leader"], dict):
        _fail("invalid context authority")
    for key in ("predecessor_context_id", "continuity_ref", "activation", "campaign"):
        if value[key] is not None and not isinstance(value[key], (str, dict)):
            _fail(f"invalid context {key}")


def _operation(operation_id: str, value: Any) -> None:
    _id(operation_id, "operation id")
    required = {"kind", "context_id", "fence", "subject_ids", "input_sha256", "expected_before", "intended_after", "idempotency_key", "state", "result_ref", "result_sha256", "observation_ref", "error"}
    value = _object(value, required, set(), "operation")
    if not isinstance(value["kind"], str) or not value["kind"] or type(value["fence"]) is not int or value["fence"] <= 0:
        _fail("invalid operation identity")
    _id(value["context_id"], "operation context")
    _digest(value["input_sha256"], "operation input_sha256")
    if not isinstance(value["idempotency_key"], str) or not value["idempotency_key"] or value["state"] not in _OPERATION_STATES:
        _fail("invalid operation state")
    if not isinstance(value["subject_ids"], list) or not value["subject_ids"] or any(not isinstance(x, str) for x in value["subject_ids"]):
        _fail("invalid operation subjects")
    if value["state"] == "CONFIRMED" and (not isinstance(value["observation_ref"], str) or not isinstance(value["result_sha256"], str)):
        _fail("confirmed operation requires observation and result digest")


def _checkpoint(checkpoint_id: str, value: Any) -> None:
    _id(checkpoint_id, "checkpoint id")
    required = {"schema", "checkpoint_id", "context_id", "previous_checkpoint_id", "state_sha256", "store_revision", "checkpoint_sha256"}
    value = _object(value, required, {"journal_anchor", "operations", "accepted_outputs", "pending_attempts"}, "checkpoint")
    if value["schema"] != CHECKPOINT_SCHEMA or value["checkpoint_id"] != checkpoint_id or type(value["store_revision"]) is not int:
        _fail("invalid checkpoint")
    _id(value["context_id"], "checkpoint context")
    _digest(value["state_sha256"], "checkpoint state_sha256")
    _digest(value["checkpoint_sha256"], "checkpoint_sha256")


def validate_block(block: Any) -> dict[str, Any]:
    required = {"schema", "work_items"}
    block = _object(block, required, set(), "agent_orchestration")
    if block["schema"] != SCHEMA or not isinstance(block["work_items"], dict):
        _fail("invalid agent_orchestration schema")
    for work_id, item in block["work_items"].items():
        _id(work_id, "orchestration work id")
        required_item = {"policy_ref", "policy_sha256", "adopted_at", "origin", "current_context_id", "contexts", "activities", "resources", "operations", "checkpoints", "checkpoint_head", "visual_decisions", "scope_files", "scope_revision", "scope_history", "last_transition"}
        item = _object(item, required_item, set(), "orchestration work item")
        if not isinstance(item["policy_ref"], str) or not item["policy_ref"] or not isinstance(item["adopted_at"], str) or not isinstance(item["origin"], dict):
            _fail("invalid orchestration origin")
        _digest(item["policy_sha256"], "policy_sha256")
        if not isinstance(item["contexts"], dict) or not isinstance(item["activities"], dict) or not isinstance(item["resources"], dict) or not isinstance(item["visual_decisions"], dict):
            _fail("invalid orchestration maps")
        if not isinstance(item["scope_files"], list) or len(set(item["scope_files"])) != len(item["scope_files"]):
            _fail("invalid scope_files")
        for path in item["scope_files"]: _safe_path(path)
        if type(item["scope_revision"]) is not int or item["scope_revision"] < 1 or not isinstance(item["scope_history"], list):
            _fail("invalid scope revision")
        for context_id, context in item["contexts"].items(): _context(context_id, context)
        epochs = [context["epoch"] for context in item["contexts"].values()]
        if len(epochs) != len(set(epochs)):
            _fail("duplicate context epoch")
        if item["current_context_id"] is not None and item["current_context_id"] not in item["contexts"]:
            _fail("unknown current context")
        if not isinstance(item["operations"], dict) or not isinstance(item["checkpoints"], dict):
            _fail("invalid operations or checkpoints")
        for operation_id, operation in item["operations"].items(): _operation(operation_id, operation)
        for checkpoint_id, checkpoint in item["checkpoints"].items(): _checkpoint(checkpoint_id, checkpoint)
        if item["checkpoint_head"] is not None and item["checkpoint_head"] not in item["checkpoints"]:
            _fail("unknown checkpoint head")
    return block


def validate_transition(previous: Any, candidate: Any) -> None:
    """Write-once adoption, histories and epochs are Store invariants."""
    if previous is None:
        validate_block(candidate); return
    before, after = validate_block(previous), validate_block(candidate)
    old_items, new_items = before["work_items"], after["work_items"]
    if not set(old_items).issubset(new_items): _fail("adopted orchestration cannot be removed")
    for work_id, old in old_items.items():
        new = new_items[work_id]
        for key in ("policy_ref", "policy_sha256", "adopted_at", "origin"):
            if old[key] != new[key]: _fail(f"write-once orchestration field: {key}")
        if new["scope_revision"] < old["scope_revision"] or new["scope_history"][:len(old["scope_history"])] != old["scope_history"]:
            _fail("scope history regression")
        if not set(old["contexts"]).issubset(new["contexts"]): _fail("context history removed")
        for context_id, context in old["contexts"].items():
            newer = new["contexts"][context_id]
            immutable = {k: v for k, v in context.items() if k != "state"}
            if any(newer.get(k) != v for k, v in immutable.items()): _fail("context immutable field changed")
            allowed = {"PREPARED": {"PREPARED", "ACTIVE"}, "ACTIVE": {"ACTIVE", "QUIESCING"}, "QUIESCING": {"QUIESCING", "RELEASED", "SUPERSEDED"}, "RELEASED": {"RELEASED"}, "SUPERSEDED": {"SUPERSEDED"}}
            if newer["state"] not in allowed[context["state"]]: _fail("invalid context transition")
        old_max = max((v["epoch"] for v in old["contexts"].values()), default=0)
        for context_id, context in new["contexts"].items():
            if context_id not in old["contexts"] and context["epoch"] <= old_max: _fail("context epoch regression")
        for operation_id, operation in old["operations"].items():
            if operation_id not in new["operations"]: _fail("operation removed")
            later = new["operations"][operation_id]
            for key in ("kind", "context_id", "fence", "subject_ids", "input_sha256", "expected_before", "intended_after", "idempotency_key"):
                if later[key] != operation[key]: _fail("operation identity changed")
            if operation["state"] == "CONFIRMED" and later != operation: _fail("confirmed operation changed")
        for checkpoint_id, checkpoint in old["checkpoints"].items():
            if new["checkpoints"].get(checkpoint_id) != checkpoint: _fail("checkpoint immutable")


def require_authority(item: dict[str, Any], context_id: str, epoch: int, session_ref: str) -> dict[str, Any]:
    context = item.get("contexts", {}).get(context_id)
    if not isinstance(context, dict) or item.get("current_context_id") != context_id or context.get("epoch") != epoch:
        _fail("LEADER-AUTHORITY-UNPROVEN")
    leader = context.get("leader", {})
    if context.get("state") != "ACTIVE" or leader.get("session_ref") != session_ref or leader.get("state") != "ACTIVE":
        _fail("LEADER-AUTHORITY-UNPROVEN")
    return context


def adoption_inputs(*, work_id: str, runtime: str, session_ref: str | None, scope_files: list[str], origin: dict[str, Any]) -> dict[str, Any]:
    """Closed, hashable adoption request.  The CLI hashes this before apply."""
    _id(work_id, "orchestration work id")
    if runtime not in {"codex", "claude"} or session_ref is not None and (not isinstance(session_ref, str) or not session_ref):
        _fail("invalid adoption runtime or session")
    if not isinstance(origin, dict):
        _fail("invalid orchestration origin")
    for path in scope_files:
        _safe_path(path)
    if len(scope_files) != len(set(scope_files)):
        _fail("duplicate scope file")
    return {"work_id": work_id, "runtime": runtime, "session_ref": session_ref,
            "scope_files": sorted(scope_files), "origin": copy.deepcopy(origin)}


def adoption_sha256(inputs: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def new_work_item(inputs: dict[str, Any], *, policy_ref: str, policy_sha256: str, adopted_at: str,
                  context_id: str | None = None) -> dict[str, Any]:
    """Build one first binding; callers still validate it under the Store lock."""
    if not isinstance(policy_ref, str) or not policy_ref:
        _fail("invalid policy ref")
    _digest(policy_sha256, "policy_sha256")
    item = {
        "policy_ref": policy_ref, "policy_sha256": policy_sha256, "adopted_at": adopted_at,
        "origin": copy.deepcopy(inputs["origin"]), "current_context_id": None, "contexts": {},
        "activities": {}, "resources": {}, "operations": {}, "checkpoints": {},
        "checkpoint_head": None, "visual_decisions": {}, "scope_files": inputs["scope_files"],
        "scope_revision": 1, "scope_history": [{"revision": 1, "files": inputs["scope_files"],
                                                     "inputs_sha256": adoption_sha256(inputs)}],
        "last_transition": None,
    }
    if context_id is None:
        return item
    _id(context_id, "context id")
    item["contexts"][context_id] = {
        "context_id": context_id, "epoch": 1, "predecessor_context_id": None,
        "continuity_ref": None, "runtime": inputs["runtime"], "adapter": inputs["runtime"],
        "activation": None, "campaign": None, "scheduler_runs": {},
        "leader": {"session_ref": inputs["session_ref"], "state": "ACTIVE", "fence": 1},
        "state": "ACTIVE", "policy_sha256": policy_sha256,
        "inputs_sha256": adoption_sha256(inputs),
    }
    item["current_context_id"] = context_id
    return item


def operation_fingerprint(kind: str, context_id: str, subjects: list[str], inputs: Any) -> str:
    data = json.dumps({"kind": kind, "context_id": context_id, "subjects": subjects, "inputs": inputs}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()
