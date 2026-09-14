"""Closed, durable portion of the agent-orchestration v1 contract.

This module is deliberately pure: the Store owns locking and durable writes.
Keeping validation here lets every Store path (CAS, transaction and WAL
recovery) apply the same rules instead of relying on CLI callers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any

try:
    from .workflow_versions import SEQUENCE_V4
except ImportError:
    from grill_core.workflow_versions import SEQUENCE_V4

SCHEMA = "grill-agent-orchestration/v1"
EVENT_SCHEMA = "grill-orchestration-event/v1"
CHECKPOINT_SCHEMA = "grill-continuity-checkpoint/v1"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_UTC_RFC3339 = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$")
_CONTEXT_STATES = {"PREPARED", "ACTIVE", "QUIESCING", "RELEASED", "SUPERSEDED"}
_OPERATION_STATES = {"INTENT", "APPLIED", "CONFIRMED", "UNKNOWN", "REFUSED"}
_LEADER_STATES = {"ACTIVE", "RELEASING", "RELEASED"}
_ACTIVITY_STATES = {"DECLARED", "BOOTSTRAPPING", "VERIFIED", "DISPATCHED", "RESULT_RECORDED", "ACCEPTED", "BLOCKED", "FAILED"}
_RESOURCE_STATES = {"REGISTERED", "CLOSE_PENDING", "REMOVE_PENDING", "CLOSED", "REMOVED", "PRESERVED", "UNKNOWN"}
_OPERATION_EDGES = {"INTENT": {"INTENT", "APPLIED", "UNKNOWN", "REFUSED"}, "APPLIED": {"APPLIED", "CONFIRMED", "UNKNOWN"}, "CONFIRMED": {"CONFIRMED"}, "UNKNOWN": {"UNKNOWN", "CONFIRMED"}, "REFUSED": {"REFUSED"}}
_ACTIVITY_EDGES = {"DECLARED": {"DECLARED", "BOOTSTRAPPING", "BLOCKED"}, "BOOTSTRAPPING": {"BOOTSTRAPPING", "VERIFIED", "BLOCKED"}, "VERIFIED": {"VERIFIED", "DISPATCHED", "BLOCKED"}, "DISPATCHED": {"DISPATCHED", "RESULT_RECORDED", "FAILED"}, "RESULT_RECORDED": {"RESULT_RECORDED", "ACCEPTED"}, "ACCEPTED": {"ACCEPTED"}, "BLOCKED": {"BLOCKED"}, "FAILED": {"FAILED"}}
_RESOURCE_EDGES = {"REGISTERED": {"REGISTERED", "CLOSE_PENDING", "REMOVE_PENDING", "PRESERVED", "UNKNOWN"}, "CLOSE_PENDING": {"CLOSE_PENDING", "CLOSED", "PRESERVED", "UNKNOWN"}, "REMOVE_PENDING": {"REMOVE_PENDING", "REMOVED", "PRESERVED", "UNKNOWN"}, "PRESERVED": {"PRESERVED", "CLOSE_PENDING", "REMOVE_PENDING"}, "UNKNOWN": {"UNKNOWN", "CLOSE_PENDING", "REMOVE_PENDING"}, "CLOSED": {"CLOSED"}, "REMOVED": {"REMOVED"}}


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


def _text(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
        _fail(f"invalid {label}")


def _known_text(value: Any, label: str) -> None:
    _text(value, label)
    if value in {"unknown", "undetermined"}:
        _fail(f"invalid {label}")


def _json(value: Any, label: str) -> None:
    """Accept only finite JSON values; maps are still closed by their caller."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        _fail(f"invalid {label}")
    if isinstance(value, list):
        for member in value:
            _json(member, label)
        return
    if isinstance(value, dict):
        for key, member in value.items():
            if not isinstance(key, str):
                _fail(f"invalid {label}")
            _json(member, label)
        return
    _fail(f"invalid {label}")


def _nullable_digest(value: Any, label: str) -> None:
    if value is not None:
        _digest(value, label)


def _ref(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    value = _object(value, {"ref", "sha256"}, set(), label)
    _text(value["ref"], f"{label} ref")
    _digest(value["sha256"], f"{label} sha256")


def _file(value: Any, label: str) -> None:
    value = _object(value, {"path", "sha256", "size", "media_type"}, set(), label)
    _safe_path(value["path"])
    _digest(value["sha256"], f"{label} sha256")
    if type(value["size"]) is not int or value["size"] < 0:
        _fail(f"invalid {label} size")
    _text(value["media_type"], f"{label} media_type")


def _unique_ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        _fail(f"invalid {label}")
    for member in value:
        _id(member, label)
    if len(set(value)) != len(value):
        _fail(f"duplicate {label}")
    return value


def _task_binding(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    value = _object(value, {"task_id", "phase", "tasks_semantic_sha256", "dag_content_sha256"}, set(), label)
    _id(value["task_id"], f"{label} task_id")
    _text(value["phase"], f"{label} phase")
    _digest(value["tasks_semantic_sha256"], f"{label} tasks_semantic_sha256")
    _digest(value["dag_content_sha256"], f"{label} dag_content_sha256")


def _input_manifest(value: Any) -> None:
    value = _object(value, {"files", "required_activity_ids", "author_activity_ids", "task_binding", "human_authorization"}, set(), "input manifest")
    if not isinstance(value["files"], list):
        _fail("invalid input manifest files")
    paths = []
    for file in value["files"]:
        _file(file, "input manifest file")
        paths.append(file["path"])
    if len(set(paths)) != len(paths):
        _fail("duplicate input manifest file")
    _unique_ids(value["required_activity_ids"], "input manifest required activity")
    _unique_ids(value["author_activity_ids"], "input manifest author activity")
    _task_binding(value["task_binding"], "input manifest task_binding", nullable=True)
    _ref(value["human_authorization"], "input manifest human_authorization", nullable=True)


def _output_manifest(value: Any) -> None:
    if value is None:
        return
    value = _object(value, {"files", "return_ref", "effect_ref"}, set(), "output manifest")
    if not isinstance(value["files"], list):
        _fail("invalid output manifest files")
    paths = []
    for file in value["files"]:
        _file(file, "output manifest file")
        paths.append(file["path"])
    if len(set(paths)) != len(paths):
        _fail("duplicate output manifest file")
    _ref(value["return_ref"], "output manifest return_ref", nullable=True)
    _ref(value["effect_ref"], "output manifest effect_ref", nullable=True)


def _manifest_sha256(value: dict[str, Any]) -> str:
    try:
        from .store import jcs_sha256
    except ImportError:
        from grill_core.store import jcs_sha256
    return jcs_sha256(value)


def _absolute_path(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
        _fail(f"invalid {label}")
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if not (posix.is_absolute() or windows.is_absolute()) or ".." in posix.parts or ".." in windows.parts:
        _fail(f"invalid {label}")


def _branch_ref(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        _fail(f"invalid {label}")
    name = value.removeprefix("refs/heads/")
    if (name == value or name in {"", "unknown", "undetermined"}
            or any(not part or part.startswith(".") or part.endswith(".lock") for part in name.split("/"))
            or ".." in value or any(char in value for char in " ~^:?*[\\")
            or value.endswith(".") or "@{" in value):
        _fail(f"invalid {label}")


def _utc_rfc3339(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _UTC_RFC3339.fullmatch(value):
        _fail(f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail(f"invalid {label}")
    if parsed.tzinfo != timezone.utc:
        _fail(f"invalid {label}")


def _oid(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _OID.fullmatch(value):
        _fail(f"invalid {label}")


def _origin(value: Any) -> None:
    value = _object(value, {"state_sha256", "metadata_sha256", "activation", "campaign", "lifecycle", "worktree"}, set(), "orchestration origin")
    _digest(value["state_sha256"], "origin state_sha256")
    _digest(value["metadata_sha256"], "origin metadata_sha256")
    _text(value["lifecycle"], "origin lifecycle", nullable=True)
    worktree = _object(value["worktree"], {"root", "branch"}, set(), "origin worktree")
    _text(worktree["root"], "origin root")
    _text(worktree["branch"], "origin branch")
    for key in ("activation", "campaign"):
        if value[key] is not None and not isinstance(value[key], dict):
            _fail(f"invalid origin {key}")
        _json(value[key], f"origin {key}")


def _leader(value: Any, epoch: int) -> None:
    value = _object(value, {"owner_id", "session_ref", "incarnation", "fence", "epoch", "state", "observation_ref", "observation_sha256"}, set(), "leader")
    _id(value["owner_id"], "leader owner_id")
    _text(value["session_ref"], "leader session_ref")
    if value["incarnation"] is not None:
        _text(value["incarnation"], "leader incarnation")
    if type(value["fence"]) is not int or value["fence"] <= 0 or value["epoch"] != epoch:
        _fail("invalid leader fence")
    if value["state"] not in _LEADER_STATES:
        _fail("invalid leader state")
    _text(value["observation_ref"], "leader observation_ref", nullable=True)
    _nullable_digest(value["observation_sha256"], "leader observation_sha256")
    if (value["observation_ref"] is None) != (value["observation_sha256"] is None):
        _fail("incomplete leader observation")


def _scheduler_runs(value: Any, contexts: dict[str, Any] | None = None) -> None:
    if not isinstance(value, dict):
        _fail("invalid scheduler_runs")
    for run_id, run in value.items():
        _id(run_id, "scheduler run id")
        run = _object(run, {"admission_sha256", "dag_sha256", "origin_context_id"}, set(), "scheduler run")
        _digest(run["admission_sha256"], "scheduler admission_sha256")
        _digest(run["dag_sha256"], "scheduler dag_sha256")
        _id(run["origin_context_id"], "scheduler origin_context_id")
        if contexts is not None and run["origin_context_id"] not in contexts:
            _fail("scheduler run has unknown origin context")


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
    _scheduler_runs(value["scheduler_runs"])
    _leader(value["leader"], value["epoch"])
    for key in ("predecessor_context_id", "continuity_ref", "activation", "campaign"):
        if value[key] is not None and not isinstance(value[key], (str, dict)):
            _fail(f"invalid context {key}")
        if isinstance(value[key], dict):
            _json(value[key], f"context {key}")
    if value["predecessor_context_id"] is not None:
        _id(value["predecessor_context_id"], "context predecessor")
    _text(value["continuity_ref"], "context continuity_ref", nullable=True)
    if "worktree_identity" in value:
        identity = _object(value["worktree_identity"], {"project_id", "work_id", "phase", "du", "git_common_dir", "real_path", "branch"}, set(), "worktree identity")
        for key in identity:
            _text(identity[key], f"worktree identity {key}")
    if "presentation" in value:
        _presentation(value["presentation"])


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
    _nullable_digest(value["result_sha256"], "operation result_sha256")
    _text(value["result_ref"], "operation result_ref", nullable=True)
    _text(value["observation_ref"], "operation observation_ref", nullable=True)
    _text(value["error"], "operation error", nullable=True)
    _json(value["expected_before"], "operation expected_before")
    _json(value["intended_after"], "operation intended_after")


def _checkpoint_digest(value: dict[str, Any]) -> str:
    try:
        from .store import jcs_sha256
    except ImportError:
        from grill_core.store import jcs_sha256
    payload = copy.deepcopy(value)
    del payload["checkpoint_sha256"]
    return jcs_sha256(payload)


def _checkpoint(checkpoint_id: str, value: Any) -> None:
    _id(checkpoint_id, "checkpoint id")
    required = {"schema", "checkpoint_id", "context_id", "previous_checkpoint_id", "worktree_identity", "created_at", "store_revision", "journal_anchor", "state_sha256", "inputs_manifest", "workflow_sha256", "constitution_sha256", "policy_sha256", "activation", "campaign", "development_sequence", "current_step", "step_states", "accepted_outputs", "accepted_executions", "pending_attempts", "scheduler_runs", "operations", "cleanup_obligations", "preserved_resources", "blocking_activity", "visual_state", "presentation", "checkpoint_sha256"}
    value = _object(value, required, set(), "checkpoint")
    if value["schema"] != CHECKPOINT_SCHEMA or value["checkpoint_id"] != checkpoint_id or type(value["store_revision"]) is not int or value["store_revision"] < 0:
        _fail("invalid checkpoint")
    _id(value["context_id"], "checkpoint context")
    _text(value["previous_checkpoint_id"], "checkpoint previous_checkpoint_id", nullable=True)
    _text(value["created_at"], "checkpoint created_at")
    for key in ("state_sha256", "workflow_sha256", "constitution_sha256", "policy_sha256", "checkpoint_sha256"):
        _digest(value[key], f"checkpoint {key}")
    for key in ("worktree_identity", "journal_anchor", "inputs_manifest", "development_sequence", "step_states", "accepted_outputs", "accepted_executions", "pending_attempts", "scheduler_runs", "operations", "cleanup_obligations", "preserved_resources", "visual_state"):
        if not isinstance(value[key], dict): _fail(f"invalid checkpoint {key}")
        _json(value[key], f"checkpoint {key}")
    for key in ("activation", "campaign"):
        if value[key] is not None and not isinstance(value[key], dict): _fail(f"invalid checkpoint {key}")
        _json(value[key], f"checkpoint {key}")
    _text(value["current_step"], "checkpoint current_step", nullable=True)
    _text(value["blocking_activity"], "checkpoint blocking_activity", nullable=True)
    if value["presentation"] is not None: _presentation(value["presentation"])
    if value["checkpoint_sha256"] != _checkpoint_digest(value): _fail("checkpoint digest mismatch")


def _activity(activity_id: str, value: Any, contexts: dict[str, Any]) -> None:
    required = {"activity_id", "context_id", "step_id", "activity_scope", "activity_type", "role", "attempt", "author_activity_ids", "input_manifest", "input_sha256", "task_binding", "runtime", "requested_model", "requested_effort", "policy_sha256", "write_files", "session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "payload_sha256", "released_at", "state", "presentation_observation_ref", "result_ref", "result_sha256", "output_manifest", "diagnostic_ref", "accepted_by_context", "acceptance_ref", "review_verdict"}
    value = _object(value, required, set(), "activity")
    _id(activity_id, "activity id")
    if value["activity_id"] != activity_id or value["context_id"] not in contexts or type(value["attempt"]) is not int or value["attempt"] < 1:
        _fail("invalid activity identity")
    if not all(isinstance(value[key], str) for key in ("activity_scope", "activity_type", "role", "state")) or value["activity_scope"] not in {"interview", "cycle"} or value["activity_type"] not in {"author", "reviewer", "deterministic_check"} or value["role"] != value["activity_type"] or value["state"] not in _ACTIVITY_STATES:
        _fail("invalid activity state")
    if value["activity_scope"] == "interview":
        if value["step_id"] is not None: _fail("interview activity has step")
    else:
        _id(value["step_id"], "activity step_id")
        if value["step_id"] not in SEQUENCE_V4:
            _fail("invalid activity step_id")
    if value["activity_type"] == "deterministic_check":
        if any(value[key] is not None for key in ("runtime", "requested_model", "requested_effort", "effective_model", "effective_effort", "resolved_model_id", "session_resource_id", "launch_observation_ref", "presentation_observation_ref", "released_at")):
            _fail("deterministic activity has runtime slots")
    else:
        if value["runtime"] not in {"codex", "claude"} or value["runtime"] != contexts[value["context_id"]]["runtime"]:
            _fail("invalid activity runtime")
        for key in ("requested_model", "requested_effort"):
            _text(value[key], f"activity {key}")
    _input_manifest(value["input_manifest"])
    if value["author_activity_ids"] != value["input_manifest"]["author_activity_ids"] or value["task_binding"] != value["input_manifest"]["task_binding"]:
        _fail("activity manifest correlation")
    _task_binding(value["task_binding"], "activity task_binding", nullable=True)
    if value["input_sha256"] != _manifest_sha256(value["input_manifest"]):
        _fail("activity input manifest digest mismatch")
    _digest(value["policy_sha256"], "activity policy_sha256")
    _unique_ids(value["author_activity_ids"], "activity author")
    if not isinstance(value["write_files"], list): _fail("invalid activity files")
    for path in value["write_files"]: _safe_path(path)
    if len(set(value["write_files"])) != len(value["write_files"]): _fail("duplicate activity files")
    if value["activity_type"] == "reviewer" and value["write_files"]:
        _fail("reviewer writes files")
    for key in ("session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "released_at", "presentation_observation_ref", "result_ref", "diagnostic_ref", "accepted_by_context", "acceptance_ref"):
        _text(value[key], f"activity {key}", nullable=True)
    if value["review_verdict"] is not None and not isinstance(value["review_verdict"], str) or value["review_verdict"] not in {None, "APPROVED", "CHANGES_REQUIRED"}:
        _fail("invalid activity review verdict")
    for key in ("payload_sha256", "result_sha256"):
        _nullable_digest(value[key], f"activity {key}")
    _output_manifest(value["output_manifest"])
    if (value["result_ref"] is None) != (value["result_sha256"] is None) or (value["result_ref"] is None) != (value["output_manifest"] is None):
        _fail("incomplete activity result")
    if (value["effective_model"] is None) != (value["effective_effort"] is None):
        _fail("incomplete activity model observation")
    if value["state"] == "DECLARED" and any(value[key] is not None for key in ("session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "payload_sha256", "released_at", "presentation_observation_ref", "result_ref", "diagnostic_ref", "accepted_by_context", "acceptance_ref", "review_verdict")):
        _fail("declared activity has observation")
    if value["state"] in {"DECLARED", "BOOTSTRAPPING", "VERIFIED"} and value["payload_sha256"] is not None:
        _fail("activity payload before dispatch")
    if value["state"] in {"DECLARED", "BOOTSTRAPPING", "VERIFIED", "DISPATCHED"} and value["result_ref"] is not None:
        _fail("activity result before record")
    if value["activity_type"] != "deterministic_check" and value["state"] == "VERIFIED" and (value["effective_model"] is None or value["effective_effort"] is None):
        _fail("verified activity lacks model observation")
    if value["state"] == "DISPATCHED" and value["payload_sha256"] is None:
        _fail("dispatched activity lacks payload")
    if value["state"] in {"RESULT_RECORDED", "ACCEPTED"} and value["result_ref"] is None:
        _fail("activity state requires result")
    if value["state"] == "ACCEPTED" and (value["accepted_by_context"] is None or value["acceptance_ref"] is None or value["review_verdict"] is None):
        _fail("accepted activity incomplete")
    if value["state"] in {"BLOCKED", "FAILED"} and value["diagnostic_ref"] is None:
        _fail("blocked activity lacks diagnostic")
    if value["output_manifest"] is not None:
        for file in value["output_manifest"]["files"]:
            if file["path"] not in value["write_files"]:
                _fail("output file outside activity grant")
        if not value["write_files"] and (value["output_manifest"]["files"] or value["output_manifest"]["return_ref"] is None):
            _fail("read-only activity lacks durable return")
        if value["task_binding"] is not None and value["write_files"] and value["output_manifest"]["effect_ref"] is None:
            _fail("task output lacks confirmed effect")


def _resource(resource_id: str, value: Any, contexts: dict[str, Any]) -> None:
    required = {"kind", "agent_id", "activity_id", "scheduler_run_id", "worker_id", "wave_id", "origin_context_id", "identity", "creation_observation", "result_acceptance_ref", "evidence_manifest", "state", "last_observation", "preservation_reasons", "operation_id"}
    value = _object(value, required, set(), "resource")
    _id(resource_id, "resource id")
    if not isinstance(value["kind"], str) or not isinstance(value["state"], str) or value["kind"] not in {"session", "worktree", "branch"} or value["origin_context_id"] not in contexts or value["state"] not in _RESOURCE_STATES:
        _fail("invalid resource state")
    for key in ("agent_id", "result_acceptance_ref", "operation_id"):
        _text(value[key], f"resource {key}", nullable=True)
    linked_activity = value["activity_id"] is not None
    scheduler_link = (value["scheduler_run_id"], value["worker_id"], value["wave_id"])
    if linked_activity == any(member is not None for member in scheduler_link):
        _fail("resource requires one creation binding")
    if linked_activity:
        _id(value["activity_id"], "resource activity_id")
    else:
        for key in ("scheduler_run_id", "worker_id", "wave_id"):
            _id(value[key], f"resource {key}")
    identity = value["identity"]
    if value["kind"] == "session":
        identity = _object(identity, {"provider", "adapter", "host", "runtime_instance", "handle", "incarnation", "owner_dispatch", "task_id", "dispatch_incarnation", "worktree_id"}, set(), "session identity")
        if not isinstance(identity["provider"], str) or not isinstance(identity["adapter"], str) or identity["provider"] not in {"codex", "claude"} or identity["adapter"] != "orca":
            _fail("invalid session identity")
        for key in ("host", "runtime_instance", "handle", "incarnation", "worktree_id"):
            _known_text(identity[key], f"session identity {key}")
        dispatch = (identity["owner_dispatch"], identity["task_id"], identity["dispatch_incarnation"])
        if any(member is None for member in dispatch) and any(member is not None for member in dispatch):
            _fail("incomplete session dispatch identity")
        for key in ("owner_dispatch", "task_id", "dispatch_incarnation"):
            if identity[key] is not None:
                _known_text(identity[key], f"session identity {key}")
    elif value["kind"] == "worktree":
        identity = _object(identity, {"git_common_dir", "worktree_key", "real_path", "branch_ref", "base_commit"}, set(), "worktree identity")
        for key in ("git_common_dir", "real_path"):
            _absolute_path(identity[key], f"worktree identity {key}")
        _known_text(identity["worktree_key"], "worktree identity worktree_key")
        _branch_ref(identity["branch_ref"], "worktree identity branch_ref")
        _oid(identity["base_commit"], "worktree identity base_commit")
    else:
        identity = _object(identity, {"git_common_dir", "branch_ref", "creation_oid", "expected_oid"}, set(), "branch identity")
        _absolute_path(identity["git_common_dir"], "branch identity git_common_dir")
        _branch_ref(identity["branch_ref"], "branch identity branch_ref")
        _oid(identity["creation_oid"], "branch identity creation_oid")
        _oid(identity["expected_oid"], "branch identity expected_oid")
    creation = _object(value["creation_observation"], {"kind", "identity", "source_ref", "source_sha256", "collected_at"}, set(), "resource creation_observation")
    if creation["kind"] != value["kind"] or creation["identity"] != identity:
        _fail("resource creation identity mismatch")
    _text(creation["source_ref"], "resource creation source_ref")
    _digest(creation["source_sha256"], "resource creation source_sha256")
    _utc_rfc3339(creation["collected_at"], "resource creation collected_at")
    evidence = _object(value["evidence_manifest"], {"files", "receipts", "terminal_head", "integrated_head"}, set(), "resource evidence_manifest")
    if not isinstance(evidence["files"], list) or not isinstance(evidence["receipts"], list):
        _fail("invalid resource evidence manifest")
    file_paths = []
    for file in evidence["files"]:
        _file(file, "resource evidence file")
        file_paths.append(file["path"])
    if len(set(file_paths)) != len(file_paths):
        _fail("duplicate resource evidence file")
    receipt_refs = []
    for receipt in evidence["receipts"]:
        _ref(receipt, "resource evidence receipt")
        receipt_refs.append(receipt["ref"])
    if len(set(receipt_refs)) != len(receipt_refs):
        _fail("duplicate resource evidence receipt")
    if value["kind"] == "session":
        if evidence["terminal_head"] is not None or evidence["integrated_head"] is not None:
            _fail("session evidence has git heads")
    else:
        _oid(evidence["terminal_head"], "resource terminal_head", nullable=True)
        _oid(evidence["integrated_head"], "resource integrated_head", nullable=True)
    _text(value["last_observation"], "resource last_observation", nullable=True)
    if value["last_observation"] is not None and value["last_observation"] not in receipt_refs:
        _fail("resource observation is not preserved")
    reasons = {"RESULT_NOT_DURABLE", "SESSION_ACTIVE", "SESSION_CLOSE_UNCONFIRMED", "IDENTITY_UNPROVEN", "IDENTITY_CHANGED", "WORKTREE_DIRTY", "IGNORED_CONTENT", "WORK_NOT_INTEGRATED", "EXCLUSIVE_EVIDENCE", "BRANCH_IN_USE", "REF_CHANGED", "PROVIDER_UNAVAILABLE"}
    if not isinstance(value["preservation_reasons"], list) or any(not isinstance(reason, str) or reason not in reasons for reason in value["preservation_reasons"]) or len(set(value["preservation_reasons"])) != len(value["preservation_reasons"]):
        _fail("invalid resource preservation_reasons")


def _presentation(value: Any) -> None:
    required = {"schema", "component", "minimum_version", "loader", "runtime", "session_identity", "config_fingerprint", "scope", "policy_sha256", "gwd_skill_sha256", "installation", "compatibility", "enablement", "trust", "loading", "behavior", "application", "suspension", "use_ready", "work_ready", "functional_verified", "diagnostics"}
    value = _object(value, required, set(), "presentation")
    if value["schema"] != "grill-gwd-presentation/v1" or value["runtime"] not in {"codex", "claude"}:
        _fail("invalid presentation")
    for key in ("component", "minimum_version", "loader", "session_identity", "config_fingerprint", "compatibility", "enablement", "trust", "loading", "behavior", "application"):
        _text(value[key], f"presentation {key}")
    _digest(value["policy_sha256"], "presentation policy_sha256")
    _digest(value["gwd_skill_sha256"], "presentation gwd_skill_sha256")
    for key in ("scope", "installation", "suspension"):
        if value[key] is not None and not isinstance(value[key], dict): _fail(f"invalid presentation {key}")
        _json(value[key], f"presentation {key}")
    if not all(type(value[key]) is bool for key in ("use_ready", "work_ready", "functional_verified")) or not isinstance(value["diagnostics"], list):
        _fail("invalid presentation projections")


def _visual_decision(decision_id: str, value: Any, contexts: dict[str, Any]) -> None:
    required = {"decision_id", "preview_sha256", "review_ref", "actor_ref", "decision", "source_ref", "recorded_at", "context_id"}
    value = _object(value, required, set(), "visual decision")
    if value["decision_id"] != decision_id or value["context_id"] not in contexts or value["decision"] not in {"approved", "rejected"}:
        _fail("invalid visual decision")
    _id(decision_id, "decision id")
    _digest(value["preview_sha256"], "visual preview_sha256")
    for key in ("review_ref", "actor_ref", "source_ref", "recorded_at"): _text(value[key], f"visual {key}")


def _scope_history(value: Any, revision: int, files: list[str]) -> None:
    if not isinstance(value, list) or len(value) != revision:
        _fail("invalid scope history")
    for number, record in enumerate(value, 1):
        record = _object(record, {"revision", "files", "inputs_sha256"}, set(), "scope history")
        if record["revision"] != number or not isinstance(record["files"], list) or len(set(record["files"])) != len(record["files"]):
            _fail("invalid scope history")
        for path in record["files"]: _safe_path(path)
        _digest(record["inputs_sha256"], "scope history inputs_sha256")
    if value[-1]["files"] != files:
        _fail("scope history does not name current files")


def validate_block(block: Any) -> dict[str, Any]:
    required = {"schema", "work_items"}
    block = _object(block, required, set(), "agent_orchestration")
    if block["schema"] != SCHEMA or not isinstance(block["work_items"], dict):
        _fail("invalid agent_orchestration schema")
    for work_id, item in block["work_items"].items():
        _id(work_id, "orchestration work id")
        required_item = {"policy_ref", "policy_sha256", "adopted_at", "origin", "current_context_id", "contexts", "activities", "resources", "operations", "checkpoints", "checkpoint_head", "visual_decisions", "scope_files", "scope_revision", "scope_history", "last_transition"}
        item = _object(item, required_item, set(), "orchestration work item")
        if not isinstance(item["policy_ref"], str) or not item["policy_ref"] or not isinstance(item["adopted_at"], str):
            _fail("invalid orchestration metadata")
        _origin(item["origin"])
        _digest(item["policy_sha256"], "policy_sha256")
        if not isinstance(item["contexts"], dict) or not isinstance(item["activities"], dict) or not isinstance(item["resources"], dict) or not isinstance(item["visual_decisions"], dict):
            _fail("invalid orchestration maps")
        if not isinstance(item["scope_files"], list) or len(set(item["scope_files"])) != len(item["scope_files"]):
            _fail("invalid scope_files")
        for path in item["scope_files"]: _safe_path(path)
        if type(item["scope_revision"]) is not int or item["scope_revision"] < 1:
            _fail("invalid scope revision")
        _scope_history(item["scope_history"], item["scope_revision"], item["scope_files"])
        for context_id, context in item["contexts"].items(): _context(context_id, context)
        epochs = [context["epoch"] for context in item["contexts"].values()]
        if len(epochs) != len(set(epochs)):
            _fail("duplicate context epoch")
        if item["current_context_id"] is not None and item["current_context_id"] not in item["contexts"]:
            _fail("unknown current context")
        for context in item["contexts"].values():
            predecessor = context["predecessor_context_id"]
            if predecessor is not None and predecessor not in item["contexts"]:
                _fail("unknown predecessor context")
            if predecessor is None and context["continuity_ref"] is not None:
                _fail("first context cannot have continuity ref")
            if predecessor is not None and context["continuity_ref"] is None:
                _fail("successor context requires continuity ref")
            _scheduler_runs(context["scheduler_runs"], item["contexts"])
        if not isinstance(item["operations"], dict) or not isinstance(item["checkpoints"], dict):
            _fail("invalid operations or checkpoints")
        idempotency = {}
        for operation_id, operation in item["operations"].items():
            _operation(operation_id, operation)
            if operation["context_id"] not in item["contexts"]: _fail("operation has unknown context")
            if operation["fence"] != item["contexts"][operation["context_id"]]["leader"]["fence"]: _fail("operation fence does not match context authority")
            identity = (operation["kind"], operation["context_id"], tuple(operation["subject_ids"]), operation["input_sha256"])
            prior = idempotency.setdefault(operation["idempotency_key"], identity)
            if prior != identity: _fail("idempotency key collides with different operation")
        for checkpoint_id, checkpoint in item["checkpoints"].items():
            _checkpoint(checkpoint_id, checkpoint)
            if checkpoint["context_id"] not in item["contexts"] or (checkpoint["previous_checkpoint_id"] is not None and checkpoint["previous_checkpoint_id"] not in item["checkpoints"]):
                _fail("checkpoint has unknown reference")
        for checkpoint_id in item["checkpoints"]:
            seen = set()
            cursor = checkpoint_id
            while cursor is not None:
                if cursor in seen: _fail("checkpoint predecessor cycle")
                seen.add(cursor)
                cursor = item["checkpoints"][cursor]["previous_checkpoint_id"]
        if item["checkpoint_head"] is not None and item["checkpoint_head"] not in item["checkpoints"]:
            _fail("unknown checkpoint head")
        for activity_id, activity in item["activities"].items():
            _activity(activity_id, activity, item["contexts"])
            if activity["policy_sha256"] != item["contexts"][activity["context_id"]]["policy_sha256"]:
                _fail("activity policy does not match context")
            if any(author not in item["activities"] for author in activity["author_activity_ids"] + activity["input_manifest"]["required_activity_ids"]): _fail("activity has unknown input activity")
            if activity["session_resource_id"] is not None and activity["session_resource_id"] not in item["resources"]: _fail("activity has unknown resource")
            if activity["accepted_by_context"] is not None and activity["accepted_by_context"] not in item["contexts"]: _fail("activity accepted by unknown context")
        for resource_id, resource in item["resources"].items():
            _resource(resource_id, resource, item["contexts"])
            if resource["activity_id"] is not None and resource["activity_id"] not in item["activities"]: _fail("resource has unknown activity")
            if resource["scheduler_run_id"] is not None and resource["scheduler_run_id"] not in item["contexts"][resource["origin_context_id"]]["scheduler_runs"]: _fail("resource has unknown scheduler run")
            if resource["operation_id"] is not None and resource["operation_id"] not in item["operations"]: _fail("resource has unknown operation")
        for activity in item["activities"].values():
            resource_id = activity["session_resource_id"]
            if resource_id is not None and item["resources"][resource_id]["kind"] != "session":
                _fail("activity resource is not a session")
            if activity["activity_type"] == "reviewer" and resource_id is not None:
                for author_id in activity["author_activity_ids"]:
                    author_resource = item["activities"][author_id]["session_resource_id"]
                    if author_resource is None or author_resource == resource_id:
                        _fail("reviewer session is not independent")
        for decision_id, decision in item["visual_decisions"].items(): _visual_decision(decision_id, decision, item["contexts"])
        if item["last_transition"] is not None:
            transition = _object(item["last_transition"], {"event_sequence", "receipt_sha256", "operation_id"}, set(), "orchestration last_transition")
            if type(transition["event_sequence"]) is not int or transition["event_sequence"] < 1: _fail("invalid orchestration last_transition")
            _digest(transition["receipt_sha256"], "last_transition receipt_sha256")
            if transition["operation_id"] not in item["operations"]: _fail("last_transition unknown operation")
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
        scope_changed = new["scope_files"] != old["scope_files"]
        if scope_changed != (new["scope_revision"] == old["scope_revision"] + 1 and len(new["scope_history"]) == len(old["scope_history"]) + 1):
            _fail("scope edit requires one explicit revision")
        if not scope_changed and (new["scope_revision"] != old["scope_revision"] or new["scope_history"] != old["scope_history"]):
            _fail("scope revision without scope edit")
        if not set(old["contexts"]).issubset(new["contexts"]): _fail("context history removed")
        for context_id, context in old["contexts"].items():
            newer = new["contexts"][context_id]
            immutable = {k: v for k, v in context.items() if k not in {"state", "activation", "campaign", "scheduler_runs", "leader", "presentation"}}
            if any(newer.get(k) != v for k, v in immutable.items()): _fail("context immutable field changed")
            allowed = {"PREPARED": {"PREPARED", "ACTIVE"}, "ACTIVE": {"ACTIVE", "QUIESCING", "SUPERSEDED"}, "QUIESCING": {"QUIESCING", "RELEASED", "SUPERSEDED"}, "RELEASED": {"RELEASED"}, "SUPERSEDED": {"SUPERSEDED"}}
            if newer["state"] not in allowed[context["state"]]: _fail("invalid context transition")
            for key in ("activation", "campaign"):
                if context[key] is not None and newer[key] != context[key]: _fail(f"context {key} is write-once")
                if context[key] is None and newer[key] is not None and not isinstance(newer[key], dict): _fail(f"invalid first {key} binding")
            for run_id, run in context["scheduler_runs"].items():
                if newer["scheduler_runs"].get(run_id) != run: _fail("scheduler run is immutable")
            old_leader, new_leader = context["leader"], newer["leader"]
            for key in ("owner_id", "session_ref", "fence", "epoch"):
                if old_leader[key] != new_leader[key]: _fail("leader identity changed")
            for key in ("incarnation", "observation_ref", "observation_sha256"):
                if old_leader[key] is not None and old_leader[key] != new_leader[key]: _fail("leader observation changed")
            leader_edges = {"ACTIVE": {"ACTIVE", "RELEASING"}, "RELEASING": {"RELEASING", "RELEASED"}, "RELEASED": {"RELEASED"}}
            if new_leader["state"] not in leader_edges[old_leader["state"]]: _fail("invalid leader transition")
        old_max = max((v["epoch"] for v in old["contexts"].values()), default=0)
        for context_id, context in new["contexts"].items():
            if context_id not in old["contexts"] and context["epoch"] <= old_max: _fail("context epoch regression")
        old_current, new_current = old["current_context_id"], new["current_context_id"]
        if old_current != new_current:
            if new_current is None: _fail("current context epoch regression")
            destination = new["contexts"][new_current]
            if old_current is None:
                if new_current in old["contexts"] or destination["predecessor_context_id"] is not None or destination["state"] != "ACTIVE": _fail("invalid first context binding")
            elif destination["predecessor_context_id"] != old_current or destination["continuity_ref"] is None or destination["state"] != "ACTIVE" or new["contexts"][old_current]["state"] != "SUPERSEDED" or destination["epoch"] <= new["contexts"][old_current]["epoch"]:
                _fail("current context requires superseded successor")
            elif new_current in old["contexts"] and old["contexts"][new_current]["state"] != "PREPARED":
                _fail("current context requires prepared successor")
        for operation_id, operation in old["operations"].items():
            if operation_id not in new["operations"]: _fail("operation removed")
            later = new["operations"][operation_id]
            for key in ("kind", "context_id", "fence", "subject_ids", "input_sha256", "expected_before", "intended_after", "idempotency_key"):
                if later[key] != operation[key]: _fail("operation identity changed")
            if operation["state"] == "CONFIRMED" and later != operation: _fail("confirmed operation changed")
            if later["state"] not in _OPERATION_EDGES[operation["state"]]: _fail("invalid operation transition")
            if operation["state"] == "UNKNOWN":
                for key in ("result_ref", "result_sha256", "observation_ref"):
                    if operation[key] is not None and later[key] != operation[key]: _fail("unknown operation evidence changed")
                if later["state"] == "CONFIRMED" and not all(isinstance(later[key], str) for key in ("result_ref", "result_sha256", "observation_ref")):
                    _fail("unknown operation reconciliation requires result and observation evidence")
        activity_identity = {"activity_id", "context_id", "step_id", "activity_scope", "activity_type", "role", "attempt", "author_activity_ids", "input_manifest", "input_sha256", "task_binding", "runtime", "requested_model", "requested_effort", "policy_sha256", "write_files"}
        if not set(old["activities"]).issubset(new["activities"]): _fail("activity history removed")
        for activity_id, activity in old["activities"].items():
            later = new["activities"][activity_id]
            if any(later[key] != activity[key] for key in activity_identity): _fail("activity identity changed")
            for key in ("session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "payload_sha256", "released_at", "presentation_observation_ref", "result_ref", "result_sha256", "output_manifest", "diagnostic_ref", "accepted_by_context", "acceptance_ref", "review_verdict"):
                if activity[key] is not None and later[key] != activity[key]:
                    _fail(f"activity first-bound field changed: {key}")
            if activity["state"] == "ACCEPTED" and later != activity: _fail("accepted activity changed")
            if later["state"] not in _ACTIVITY_EDGES[activity["state"]]: _fail("invalid activity transition")
        resource_identity = {"kind", "agent_id", "activity_id", "scheduler_run_id", "worker_id", "wave_id", "origin_context_id", "identity", "creation_observation"}
        if not set(old["resources"]).issubset(new["resources"]): _fail("resource history removed")
        for resource_id, resource in old["resources"].items():
            later = new["resources"][resource_id]
            if any(later[key] != resource[key] for key in resource_identity): _fail("resource identity changed")
            old_evidence, later_evidence = resource["evidence_manifest"], later["evidence_manifest"]
            old_files = {file["path"]: file for file in old_evidence["files"]}
            later_files = {file["path"]: file for file in later_evidence["files"]}
            old_receipts = {receipt["ref"]: receipt for receipt in old_evidence["receipts"]}
            later_receipts = {receipt["ref"]: receipt for receipt in later_evidence["receipts"]}
            if any(later_files.get(path) != file for path, file in old_files.items()) or any(later_receipts.get(ref) != receipt for ref, receipt in old_receipts.items()):
                _fail("resource evidence changed")
            for key in ("terminal_head", "integrated_head"):
                if old_evidence[key] is not None and later_evidence[key] != old_evidence[key]:
                    _fail("resource evidence head changed")
            if later["state"] not in _RESOURCE_EDGES[resource["state"]]: _fail("invalid resource transition")
        if not set(old["visual_decisions"]).issubset(new["visual_decisions"]): _fail("visual decision history removed")
        for decision_id, decision in old["visual_decisions"].items():
            if new["visual_decisions"][decision_id] != decision: _fail("visual decision history changed")
        for checkpoint_id, checkpoint in old["checkpoints"].items():
            if new["checkpoints"].get(checkpoint_id) != checkpoint: _fail("checkpoint immutable")
        old_head, new_head = old["checkpoint_head"], new["checkpoint_head"]
        if old_head is not None:
            if new_head is None: _fail("checkpoint head cannot be cleared")
            cursor = new_head
            while cursor != old_head:
                predecessor = new["checkpoints"][cursor]["previous_checkpoint_id"]
                if predecessor is None: _fail("checkpoint head regression")
                cursor = predecessor


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
        "leader": {"owner_id": context_id, "session_ref": inputs["session_ref"],
                   "incarnation": None, "fence": 1, "epoch": 1, "state": "ACTIVE",
                   "observation_ref": None, "observation_sha256": None},
        "state": "ACTIVE", "policy_sha256": policy_sha256,
        "inputs_sha256": adoption_sha256(inputs),
    }
    item["current_context_id"] = context_id
    return item


def operation_fingerprint(kind: str, context_id: str, subjects: list[str], inputs: Any) -> str:
    data = json.dumps({"kind": kind, "context_id": context_id, "subjects": subjects, "inputs": inputs}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()
