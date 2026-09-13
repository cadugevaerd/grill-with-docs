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
import re
from typing import Any

SCHEMA = "grill-agent-orchestration/v1"
EVENT_SCHEMA = "grill-orchestration-event/v1"
CHECKPOINT_SCHEMA = "grill-continuity-checkpoint/v1"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONTEXT_STATES = {"PREPARED", "ACTIVE", "QUIESCING", "RELEASED", "SUPERSEDED"}
_OPERATION_STATES = {"INTENT", "APPLIED", "CONFIRMED", "UNKNOWN", "REFUSED"}
_LEADER_STATES = {"ACTIVE", "RELEASING", "RELEASED"}
_ACTIVITY_STATES = {"DECLARED", "BOOTSTRAPPING", "VERIFIED", "DISPATCHED", "RESULT_RECORDED", "ACCEPTED", "BLOCKED", "FAILED"}
_RESOURCE_STATES = {"REGISTERED", "CLOSE_PENDING", "REMOVE_PENDING", "CLOSED", "REMOVED", "PRESERVED", "UNKNOWN"}


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
    if not isinstance(value, str) or not value:
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


def _checkpoint(checkpoint_id: str, value: Any) -> None:
    _id(checkpoint_id, "checkpoint id")
    required = {"schema", "checkpoint_id", "context_id", "previous_checkpoint_id", "worktree_identity", "created_at", "store_revision", "journal_anchor", "state_sha256", "inputs_manifest", "workflow_sha256", "constitution_sha256", "policy_sha256", "activation", "campaign", "development_sequence", "current_step", "step_states", "accepted_outputs", "accepted_executions", "pending_attempts", "scheduler_runs", "operations", "cleanup_obligations", "preserved_resources", "blocking_activity", "visual_state", "presentation", "checkpoint_sha256"}
    value = _object(value, required, set(), "checkpoint")
    if value["schema"] != CHECKPOINT_SCHEMA or value["checkpoint_id"] != checkpoint_id or type(value["store_revision"]) is not int:
        _fail("invalid checkpoint")
    _id(value["context_id"], "checkpoint context")
    _text(value["previous_checkpoint_id"], "checkpoint previous_checkpoint_id", nullable=True)
    _text(value["created_at"], "checkpoint created_at")
    for key in ("state_sha256", "workflow_sha256", "constitution_sha256", "policy_sha256", "checkpoint_sha256"):
        _digest(value[key], f"checkpoint {key}")
    for key in ("worktree_identity", "journal_anchor", "inputs_manifest", "activation", "campaign", "development_sequence", "step_states", "accepted_outputs", "accepted_executions", "pending_attempts", "scheduler_runs", "operations", "cleanup_obligations", "preserved_resources", "visual_state"):
        if not isinstance(value[key], dict): _fail(f"invalid checkpoint {key}")
        _json(value[key], f"checkpoint {key}")
    _text(value["current_step"], "checkpoint current_step", nullable=True)
    _text(value["blocking_activity"], "checkpoint blocking_activity", nullable=True)
    if value["presentation"] is not None: _presentation(value["presentation"])


def _activity(activity_id: str, value: Any, contexts: dict[str, Any]) -> None:
    required = {"activity_id", "context_id", "step_id", "activity_scope", "activity_type", "role", "attempt", "author_activity_ids", "input_manifest", "input_sha256", "task_binding", "runtime", "requested_model", "requested_effort", "policy_sha256", "write_files", "session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "payload_sha256", "released_at", "state", "presentation_observation_ref", "result_ref", "result_sha256", "output_manifest", "diagnostic_ref", "accepted_by_context", "acceptance_ref", "review_verdict"}
    value = _object(value, required, set(), "activity")
    _id(activity_id, "activity id")
    if value["activity_id"] != activity_id or value["context_id"] not in contexts or type(value["attempt"]) is not int or value["attempt"] < 1:
        _fail("invalid activity identity")
    if value["step_id"] is not None: _id(value["step_id"], "activity step_id")
    for key in ("activity_scope", "activity_type", "role", "runtime", "requested_model", "requested_effort"):
        _text(value[key], f"activity {key}")
    if value["runtime"] not in {"codex", "claude"} or value["state"] not in _ACTIVITY_STATES:
        _fail("invalid activity state")
    _digest(value["input_sha256"], "activity input_sha256")
    _digest(value["policy_sha256"], "activity policy_sha256")
    if not isinstance(value["author_activity_ids"], list) or len(set(value["author_activity_ids"])) != len(value["author_activity_ids"]):
        _fail("invalid activity authors")
    for author in value["author_activity_ids"]: _id(author, "activity author")
    if not isinstance(value["write_files"], list) or len(set(value["write_files"])) != len(value["write_files"]): _fail("invalid activity files")
    for path in value["write_files"]: _safe_path(path)
    for key in ("session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "released_at", "presentation_observation_ref", "result_ref", "diagnostic_ref", "accepted_by_context", "acceptance_ref", "review_verdict"):
        _text(value[key], f"activity {key}", nullable=True)
    for key in ("payload_sha256", "result_sha256"):
        _nullable_digest(value[key], f"activity {key}")
    for key in ("input_manifest", "task_binding", "output_manifest"):
        _json(value[key], f"activity {key}")


def _resource(resource_id: str, value: Any, contexts: dict[str, Any]) -> None:
    required = {"kind", "agent_id", "activity_id", "scheduler_run_id", "worker_id", "wave_id", "origin_context_id", "identity", "creation_observation", "result_acceptance_ref", "evidence_manifest", "state", "last_observation", "preservation_reasons", "operation_id"}
    value = _object(value, required, set(), "resource")
    _id(resource_id, "resource id")
    if value["kind"] not in {"session", "worktree", "branch"} or value["origin_context_id"] not in contexts or value["state"] not in _RESOURCE_STATES:
        _fail("invalid resource state")
    for key in ("agent_id", "activity_id", "scheduler_run_id", "worker_id", "wave_id", "result_acceptance_ref", "last_observation", "operation_id"):
        _text(value[key], f"resource {key}", nullable=True)
    for key in ("identity", "creation_observation", "evidence_manifest"):
        if not isinstance(value[key], dict): _fail(f"invalid resource {key}")
        _json(value[key], f"resource {key}")
    if not isinstance(value["preservation_reasons"], list) or any(not isinstance(reason, str) or not reason for reason in value["preservation_reasons"]):
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
        for operation_id, operation in item["operations"].items():
            _operation(operation_id, operation)
            if operation["context_id"] not in item["contexts"]: _fail("operation has unknown context")
        for checkpoint_id, checkpoint in item["checkpoints"].items():
            _checkpoint(checkpoint_id, checkpoint)
            if checkpoint["context_id"] not in item["contexts"] or (checkpoint["previous_checkpoint_id"] is not None and checkpoint["previous_checkpoint_id"] not in item["checkpoints"]):
                _fail("checkpoint has unknown reference")
        if item["checkpoint_head"] is not None and item["checkpoint_head"] not in item["checkpoints"]:
            _fail("unknown checkpoint head")
        for activity_id, activity in item["activities"].items():
            _activity(activity_id, activity, item["contexts"])
            if any(author not in item["activities"] for author in activity["author_activity_ids"]): _fail("activity has unknown author")
            if activity["session_resource_id"] is not None and activity["session_resource_id"] not in item["resources"]: _fail("activity has unknown resource")
            if activity["accepted_by_context"] is not None and activity["accepted_by_context"] not in item["contexts"]: _fail("activity accepted by unknown context")
        for resource_id, resource in item["resources"].items():
            _resource(resource_id, resource, item["contexts"])
            if resource["activity_id"] is not None and resource["activity_id"] not in item["activities"]: _fail("resource has unknown activity")
            if resource["operation_id"] is not None and resource["operation_id"] not in item["operations"]: _fail("resource has unknown operation")
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
            if new_current is None or new_current in old["contexts"]: _fail("current context epoch regression")
            destination = new["contexts"][new_current]
            if old_current is None:
                if destination["predecessor_context_id"] is not None or destination["state"] != "ACTIVE": _fail("invalid first context binding")
            elif destination["predecessor_context_id"] != old_current or destination["continuity_ref"] is None or destination["state"] != "ACTIVE" or new["contexts"][old_current]["state"] != "SUPERSEDED":
                _fail("current context requires superseded successor")
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
