"""Closed, durable portion of the agent-orchestration v1 contract.

This module is deliberately pure: the Store owns locking and durable writes.
Keeping validation here lets every Store path (CAS, transaction and WAL
recovery) apply the same rules instead of relying on CLI callers.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any, Mapping

try:
    from .workflow_versions import SEQUENCE_V4
except ImportError:
    from grill_core.workflow_versions import SEQUENCE_V4

SCHEMA = "grill-agent-orchestration/v1"
EVENT_SCHEMA = "grill-orchestration-event/v1"
CHECKPOINT_SCHEMA = "grill-continuity-checkpoint/v1"
CHECKPOINT_REQUEST_SCHEMA = "grill-checkpoint-request/v1"
CHECKPOINT_CONTENT_SCHEMA = "grill-checkpoint-content/v1"
MAX_CHECKPOINT_STATE_BYTES = 8 * 1024 * 1024
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
_CAMPAIGN_FIELDS = ("project_id", "run_id", "runtime", "adapter", "registry_sha256", "recovery_generation_id", "plan_revision")
_ATTESTATION_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECOVERY_GENERATION = re.compile(r"^rg-[0-9a-f]{64}$")

# The leader's recommendation is deliberately absent here.  These are the
# only pairs that may author or review a technical decision; an unavailable
# pair blocks instead of falling back to the leader or a frontier worker.
SPECIALIST_PAIRS = {
    "codex": {"author": ("gpt-6-astra", "xhigh"), "reviewer": ("gpt-6-astra", "high")},
    "claude": {"author": ("fable", "xhigh"), "reviewer": ("fable", "high")},
}
_SESSION_IDENTITY_FIELDS = (
    "provider", "adapter", "host", "runtime_instance", "handle", "incarnation",
    "owner_dispatch", "task_id", "dispatch_incarnation", "worktree_id",
)
_ACTIVITY_CONTEXT_SCHEMA = "grill-activity-context/v1"
_ACTIVITY_PAYLOAD_SCHEMA = "grill-activity-payload/v1"


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


def campaign(value: Any) -> dict[str, Any]:
    """Validate the seven immutable fields which identify one campaign."""
    value = _object(value, set(_CAMPAIGN_FIELDS), set(), "campaign")
    if (not isinstance(value["project_id"], str) or not _ATTESTATION_DIGEST.fullmatch(value["project_id"])
            or not isinstance(value["run_id"], str) or not value["run_id"]
            or value["runtime"] not in {"codex", "claude"}
            or not isinstance(value["adapter"], str) or not value["adapter"]
            or not isinstance(value["registry_sha256"], str) or not _ATTESTATION_DIGEST.fullmatch(value["registry_sha256"])
            or not isinstance(value["recovery_generation_id"], str) or not _RECOVERY_GENERATION.fullmatch(value["recovery_generation_id"])
            or type(value["plan_revision"]) is not int or value["plan_revision"] < 0):
        _fail("invalid campaign")
    return value


def successor_campaign(previous: Mapping[str, Any], *, runtime: str, adapter: str,
                       registry_sha256: str, bridge_seed: Mapping[str, Any]) -> dict[str, Any]:
    """Mint only the recovery generation while carrying the logical campaign."""
    previous = campaign(dict(previous))
    if runtime not in {"codex", "claude"} or not isinstance(adapter, str) or not adapter:
        _fail("invalid successor runtime")
    if not isinstance(registry_sha256, str) or not _ATTESTATION_DIGEST.fullmatch(registry_sha256):
        _fail("invalid successor registry")
    digest = hashlib.sha256(json.dumps({"previous": previous, "runtime": runtime,
        "adapter": adapter, "registry_sha256": registry_sha256, "bridge": bridge_seed},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return campaign({"project_id": previous["project_id"], "run_id": previous["run_id"],
        "runtime": runtime, "adapter": adapter, "registry_sha256": registry_sha256,
        "recovery_generation_id": "rg-" + digest, "plan_revision": previous["plan_revision"]})


def campaign_bridge(previous: Mapping[str, Any], successor: Mapping[str, Any], *,
                    accepted_outputs: Mapping[str, Any], worktree_identity: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact historical bridge accepted for one successor entry."""
    old, new = campaign(dict(previous)), campaign(dict(successor))
    if old["project_id"] != new["project_id"] or old["run_id"] != new["run_id"] or old["plan_revision"] != new["plan_revision"]:
        _fail("campaign bridge substitutes project, run, or plan")
    if old["recovery_generation_id"] == new["recovery_generation_id"]:
        _fail("campaign bridge did not mint a successor generation")
    if not isinstance(accepted_outputs, Mapping) or not isinstance(worktree_identity, Mapping):
        _fail("invalid campaign bridge")
    _json(dict(accepted_outputs), "campaign bridge accepted outputs")
    _json(dict(worktree_identity), "campaign bridge worktree identity")
    return {"from_campaign": copy.deepcopy(old), "to_campaign": copy.deepcopy(new),
            "accepted_outputs": copy.deepcopy(dict(accepted_outputs)),
            "worktree_identity": copy.deepcopy(dict(worktree_identity))}


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


def specialist_pair(runtime: str, activity_type: str) -> tuple[str, str]:
    """Return the exact effective pair required for one specialist role."""
    try:
        return SPECIALIST_PAIRS[runtime][activity_type]
    except KeyError as exc:
        raise OrchestrationError("SPECIALIST-CAPABILITY-UNPROVEN") from exc


def activity_input_sha256(manifest: dict[str, Any]) -> str:
    """Validate and hash the immutable activity input before a bootstrap."""
    _input_manifest(manifest)
    return _manifest_sha256(manifest)


def activity_payload(activity: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    """Build the technical payload only after the stored VERIFIED boundary."""
    activity = dict(activity)
    context = dict(context)
    if activity.get("state") not in {"VERIFIED", "DISPATCHED"}:
        _fail("ACTIVITY-NOT-VERIFIED")
    if (activity.get("context_id") != context.get("context_id")
            or (activity.get("activity_type") != "deterministic_check"
                and activity.get("runtime") != context.get("runtime"))
            or not isinstance(context.get("leader"), dict)):
        _fail("CONTEXT-FENCED")
    fence = context["leader"].get("fence")
    if type(fence) is not int or fence < 1:
        _fail("CONTEXT-FENCED")
    return {
        "schema": _ACTIVITY_PAYLOAD_SCHEMA,
        "activity_id": activity["activity_id"],
        "context_id": activity["context_id"],
        "fence": fence,
        "runtime": activity["runtime"],
        "input_sha256": activity["input_sha256"],
        "input_manifest": copy.deepcopy(activity["input_manifest"]),
        "write_files": copy.deepcopy(activity["write_files"]),
    }


def bootstrap_request(activity: Mapping[str, Any]) -> dict[str, Any]:
    """The first contact carries identity/configuration only, never work."""
    activity = dict(activity)
    if activity.get("state") not in {"DECLARED", "BOOTSTRAPPING"}:
        _fail("INVALID-ACTIVITY-TRANSITION")
    if activity.get("activity_type") == "deterministic_check":
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    return {
        "activity_id": activity["activity_id"],
        "context_id": activity["context_id"],
        "runtime": activity["runtime"],
        "requested_model": activity["requested_model"],
        "requested_effort": activity["requested_effort"],
        "transport": "bootstrap",
    }


def verify_specialist(activity: Mapping[str, Any], observation: Mapping[str, Any], *,
                      require_open: bool = True) -> dict[str, Any]:
    """Reject requested-only, aliased, or changed effective specialist facts."""
    try:
        from .agent_runtime import validate_observation
    except ImportError:
        from grill_core.agent_runtime import validate_observation
    activity = dict(activity)
    observed = validate_observation(dict(observation))
    if activity.get("activity_type") not in {"author", "reviewer"}:
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    expected_model, expected_effort = specialist_pair(activity.get("runtime"), activity["activity_type"])
    if activity.get("requested_model") != expected_model or activity.get("requested_effort") != expected_effort:
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    if observed["provider"] != activity["runtime"]:
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    if observed["effective_model"] != expected_model:
        _fail("SPECIALIST-MODEL-DIVERGENT")
    if observed["effective_effort"] != expected_effort:
        _fail("SPECIALIST-EFFORT-DIVERGENT")
    if observed["resolved_model_id"] != expected_model:
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    if require_open and (observed["activity"] not in {"active", "idle"} or observed["close"] != "not_requested"):
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    return observed


def activity_requirements(policy: Mapping[str, Any], *, step_id: str | None,
                          activity_scope: str, new_how: bool = False,
                          frontend: bool = False) -> tuple[str, ...]:
    """Return policy roles; a delivered context is intentionally not proof."""
    if activity_scope == "interview":
        interview = policy.get("interview") if isinstance(policy, Mapping) else None
        if not isinstance(interview, Mapping) or step_id is not None:
            _fail("ACTIVITY-REQUIRED")
        roles = interview.get("roles")
        if not isinstance(roles, list) or any(role not in {"author", "reviewer"} for role in roles):
            _fail("ACTIVITY-REQUIRED")
        return tuple(roles)
    matrix = policy.get("activity_matrix") if isinstance(policy, Mapping) else None
    entry = matrix.get(step_id) if isinstance(matrix, Mapping) else None
    if not isinstance(entry, Mapping):
        _fail("ACTIVITY-REQUIRED")
    required = entry.get("required")
    if not isinstance(required, list) or any(not isinstance(role, str) for role in required):
        _fail("ACTIVITY-REQUIRED")
    roles = {role for role in required if role in {"author", "reviewer"}}
    if "reviewer_independent_of_all_authors" in required:
        roles.add("reviewer")
    if new_how and "reviewer_if_judgment" in required:
        roles.add("reviewer")
    if new_how and "author_and_reviewer_for_new_judgment" in required:
        roles.update(("author", "reviewer"))
    if new_how and any(entry.get(key) is True for key in (
            "author_for_new_how", "author_for_redesign", "author_for_new_decision",
            "author_for_additional_plan")):
        roles.add("author")
    if new_how and entry.get("reviewer_for_judgment") is True:
        roles.add("reviewer")
    if frontend and step_id == "plan":
        roles.update(("author", "reviewer"))
    return tuple(sorted(roles))


def _reviewer_authors(activity: Mapping[str, Any], activities: Mapping[str, Any], *,
                      require_accepted: bool) -> tuple[Mapping[str, Any], ...]:
    """Resolve the declared complete author chain for a reviewer."""
    if activity.get("activity_type") != "reviewer":
        return ()
    author_ids = activity.get("author_activity_ids")
    if not isinstance(author_ids, list) or not author_ids:
        _fail("REVIEWER-NOT-INDEPENDENT")
    authors: list[Mapping[str, Any]] = []
    for author_id in author_ids:
        author = activities.get(author_id)
        if not isinstance(author, Mapping) or author.get("activity_type") != "author":
            _fail("REVIEWER-NOT-INDEPENDENT")
        if require_accepted and author.get("state") != "ACCEPTED":
            _fail("REVIEWER-NOT-INDEPENDENT")
        authors.append(author)
    required_ids = activity.get("input_manifest", {}).get("required_activity_ids")
    if isinstance(required_ids, list):
        required_authors = {
            author_id for author_id in required_ids
            if isinstance(activities.get(author_id), Mapping)
            and activities[author_id].get("activity_type") == "author"
        }
        if required_authors and required_authors != set(author_ids):
            _fail("REVIEWER-NOT-INDEPENDENT")
    return tuple(authors)


def require_reviewer_independence(activity: Mapping[str, Any], observation: Mapping[str, Any], *,
                                  activities: Mapping[str, Any], resources: Mapping[str, Any]) -> None:
    """A different activity id is not a different reviewer session."""
    if activity.get("activity_type") != "reviewer":
        return
    try:
        from .agent_runtime import session_identity, validate_observation
    except ImportError:
        from grill_core.agent_runtime import session_identity, validate_observation
    observed = validate_observation(dict(observation))
    reviewer_identity = session_identity(observed)
    for author in _reviewer_authors(activity, activities, require_accepted=True):
        resource_id = author.get("session_resource_id")
        resource = resources.get(resource_id)
        if not isinstance(resource, Mapping) or resource.get("activity_id") != author.get("activity_id"):
            _fail("REVIEWER-NOT-INDEPENDENT")
        identity = resource.get("identity")
        if not isinstance(identity, Mapping):
            _fail("REVIEWER-NOT-INDEPENDENT")
        try:
            author_identity = session_identity(dict(identity))
        except Exception as exc:
            raise OrchestrationError("REVIEWER-NOT-INDEPENDENT") from exc
        if author_identity == reviewer_identity:
            _fail("REVIEWER-NOT-INDEPENDENT")


def activity_coverage(item: Mapping[str, Any], policy: Mapping[str, Any], *, context_id: str,
                      step_id: str | None, activity_scope: str = "cycle",
                      new_how: bool = False, frontend: bool = False) -> dict[str, Any]:
    """Prove accepted activities, never merely that their context was sent."""
    required = activity_requirements(policy, step_id=step_id, activity_scope=activity_scope,
                                     new_how=new_how, frontend=frontend)
    accepted: dict[str, list[str]] = {role: [] for role in required}
    changes_required: list[str] = []
    stale: list[str] = []
    for activity_id, activity in item.get("activities", {}).items():
        if not isinstance(activity, Mapping) or activity.get("state") != "ACCEPTED":
            continue
        if (activity.get("context_id") != context_id or activity.get("activity_scope") != activity_scope
                or activity.get("step_id") != step_id or activity.get("activity_type") not in accepted):
            continue
        if activity["activity_type"] == "reviewer":
            verdict = activity.get("review_verdict")
            if verdict == "CHANGES_REQUIRED":
                changes_required.append(activity_id)
                continue
            if verdict == "STALE":
                stale.append(activity_id)
                continue
            if verdict != "APPROVED":
                continue
            try:
                _reviewer_authors(activity, item.get("activities", {}), require_accepted=True)
            except OrchestrationError:
                continue
        accepted[activity["activity_type"]].append(activity_id)
    missing = [role for role, ids in accepted.items() if not ids]
    return {"required": list(required), "accepted": {role: sorted(ids) for role, ids in accepted.items()},
            "changes_required": sorted(changes_required), "stale": sorted(stale), "missing": missing}


def require_activity_coverage(item: Mapping[str, Any], policy: Mapping[str, Any], *, context_id: str,
                              step_id: str | None, activity_scope: str = "cycle",
                              new_how: bool = False, frontend: bool = False) -> dict[str, Any]:
    coverage = activity_coverage(item, policy, context_id=context_id, step_id=step_id,
                                 activity_scope=activity_scope, new_how=new_how, frontend=frontend)
    if coverage["missing"]:
        _fail("ACTIVITY-REQUIRED: " + ", ".join(coverage["missing"]))
    return coverage


def invocation_context(*, policy: Mapping[str, Any], policy_sha256: str,
                       context: Mapping[str, Any], step_id: str,
                       canonical_entrypoint: Mapping[str, Any], supplement: Mapping[str, Any],
                       task_template: Mapping[str, Any], new_how: bool = False,
                       frontend: bool = False) -> dict[str, Any]:
    """Return hashed supplements alongside, never instead of, the entrypoint."""
    _digest(policy_sha256, "policy sha256")
    if not isinstance(canonical_entrypoint, Mapping) or not isinstance(supplement, Mapping) or not isinstance(task_template, Mapping):
        _fail("INVALID-INVOCATION-CONTEXT")
    requirements = activity_requirements(policy, step_id=step_id, activity_scope="cycle",
                                         new_how=new_how, frontend=frontend)
    return {
        "schema": _ACTIVITY_CONTEXT_SCHEMA,
        "context_id": context["context_id"],
        "epoch": context["epoch"],
        "step_id": step_id,
        "canonical_entrypoint": copy.deepcopy(dict(canonical_entrypoint)),
        "policy_sha256": policy_sha256,
        "supplement": copy.deepcopy(dict(supplement)),
        "task_template": copy.deepcopy(dict(task_template)),
        "required_activities": list(requirements),
        "limitation": "context-delivery-is-not-skill-invocation",
    }


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
    if value["campaign"] is not None:
        campaign(value["campaign"])
    if "worktree_identity" in value:
        identity = _object(value["worktree_identity"], {"project_id", "work_id", "phase", "du", "git_common_dir", "real_path", "branch"}, set(), "worktree identity")
        for key in identity:
            _text(identity[key], f"worktree identity {key}")
    if "presentation" in value:
        _presentation(value["presentation"])


def _operation(operation_id: str, value: Any) -> None:
    _id(operation_id, "operation id")
    required = {"kind", "context_id", "fence", "subject_ids", "input_sha256", "expected_before", "intended_after", "idempotency_key", "state", "result_ref", "result_sha256", "observation_ref", "error"}
    value = _object(value, required, {"request", "content_ref"}, "operation")
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
    if ("request" in value) != ("content_ref" in value):
        _fail("incomplete checkpoint operation content")
    if "request" in value:
        validate_checkpoint_request(value["request"])
        _text(value["content_ref"], "operation content_ref")


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
    for key in ("worktree_identity", "journal_anchor", "inputs_manifest", "step_states", "accepted_outputs", "accepted_executions", "pending_attempts", "scheduler_runs", "operations", "cleanup_obligations", "preserved_resources", "visual_state"):
        if not isinstance(value[key], dict): _fail(f"invalid checkpoint {key}")
        _json(value[key], f"checkpoint {key}")
    if not isinstance(value["development_sequence"], (dict, list)):
        _fail("invalid checkpoint development_sequence")
    _json(value["development_sequence"], "checkpoint development_sequence")
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
    for path in value["write_files"]:
        _safe_path(path)
        if path == ".grill" or path.startswith(".grill/") or path == ".specify/reports" or path.startswith(".specify/reports/"):
            _fail("activity writes leader evidence")
    if len(set(value["write_files"])) != len(value["write_files"]): _fail("duplicate activity files")
    if value["activity_type"] == "reviewer" and value["write_files"]:
        _fail("reviewer writes files")
    for key in ("session_resource_id", "launch_observation_ref", "effective_model", "effective_effort", "resolved_model_id", "released_at", "presentation_observation_ref", "result_ref", "diagnostic_ref", "accepted_by_context", "acceptance_ref"):
        _text(value[key], f"activity {key}", nullable=True)
    if (value["review_verdict"] is not None and not isinstance(value["review_verdict"], str)
            or value["review_verdict"] not in {None, "APPROVED", "CHANGES_REQUIRED", "STALE"}):
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
    if value["activity_type"] != "deterministic_check" and value["state"] in {"VERIFIED", "DISPATCHED", "RESULT_RECORDED", "ACCEPTED"}:
        if any(value[key] is None for key in ("session_resource_id", "launch_observation_ref",
                                              "effective_model", "effective_effort", "resolved_model_id")):
            _fail("specialist activity lacks session observation")
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


def new_activity(*, activity_id: str, context_id: str, step_id: str | None,
                 activity_scope: str, activity_type: str, attempt: int,
                 input_manifest: dict[str, Any], policy_sha256: str,
                 write_files: list[str]) -> dict[str, Any]:
    """Create the durable neutral-bootstrap record for one activity."""
    if activity_scope not in {"interview", "cycle"}:
        _fail("invalid activity scope")
    if activity_scope == "interview" and step_id is not None:
        _fail("interview activity has step")
    if activity_scope == "cycle" and step_id not in SEQUENCE_V4:
        _fail("invalid activity step_id")
    _id(activity_id, "activity id")
    _id(context_id, "activity context")
    if type(attempt) is not int or attempt < 1:
        _fail("invalid activity attempt")
    if activity_type not in {"author", "reviewer", "deterministic_check"}:
        _fail("invalid activity type")
    if activity_type == "reviewer" and write_files:
        _fail("reviewer writes files")
    input_manifest = copy.deepcopy(input_manifest)
    input_sha256 = activity_input_sha256(input_manifest)
    if activity_type == "deterministic_check":
        runtime = requested_model = requested_effort = None
    else:
        runtime = None
        # Runtime is supplied by the owning context during prepare. This keeps
        # this constructor usable for a context switch without guessing it.
        requested_model = requested_effort = None
    return {
        "activity_id": activity_id, "context_id": context_id, "step_id": step_id,
        "activity_scope": activity_scope, "activity_type": activity_type, "role": activity_type,
        "attempt": attempt, "author_activity_ids": input_manifest["author_activity_ids"],
        "input_manifest": input_manifest, "input_sha256": input_sha256,
        "task_binding": input_manifest["task_binding"], "runtime": runtime,
        "requested_model": requested_model, "requested_effort": requested_effort,
        "policy_sha256": policy_sha256, "write_files": sorted(write_files),
        "session_resource_id": None, "launch_observation_ref": None,
        "effective_model": None, "effective_effort": None, "resolved_model_id": None,
        "payload_sha256": None, "released_at": None, "state": "DECLARED",
        "presentation_observation_ref": None, "result_ref": None, "result_sha256": None,
        "output_manifest": None, "diagnostic_ref": None, "accepted_by_context": None,
        "acceptance_ref": None, "review_verdict": None,
    }


def prepare_activity(activity: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    """Bind exact policy credentials and return a bootstrap-only activity."""
    prepared = copy.deepcopy(dict(activity))
    if prepared.get("state") not in {"DECLARED", "BOOTSTRAPPING"}:
        _fail("INVALID-ACTIVITY-TRANSITION")
    if prepared.get("context_id") != context.get("context_id"):
        _fail("CONTEXT-FENCED")
    if prepared["activity_type"] != "deterministic_check":
        runtime = context.get("runtime")
        model, effort = specialist_pair(runtime, prepared["activity_type"])
        prepared["runtime"], prepared["requested_model"], prepared["requested_effort"] = runtime, model, effort
    if prepared["activity_type"] == "reviewer" and prepared["write_files"]:
        _fail("reviewer writes files")
    prepared["state"] = "BOOTSTRAPPING"
    return prepared


def record_verified_activity(activity: Mapping[str, Any], observation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Persist only a freshly verified effective identity before payload use."""
    verified = copy.deepcopy(dict(activity))
    if verified.get("state") != "BOOTSTRAPPING":
        _fail("INVALID-ACTIVITY-TRANSITION")
    if verified.get("activity_type") == "deterministic_check":
        if observation is not None:
            _fail("deterministic activity has observation")
        verified["state"] = "VERIFIED"
        return verified
    if observation is None:
        _fail("SPECIALIST-CAPABILITY-UNPROVEN")
    observed = verify_specialist(verified, observation)
    verified.update({
        "session_resource_id": specialist_resource_id(verified["activity_id"]),
        "launch_observation_ref": observed["source_ref"],
        "effective_model": observed["effective_model"],
        "effective_effort": observed["effective_effort"],
        "resolved_model_id": observed["resolved_model_id"],
        "state": "VERIFIED",
    })
    return verified


def specialist_resource_id(activity_id: str) -> str:
    _id(activity_id, "activity id")
    return "session-" + hashlib.sha256(activity_id.encode("utf-8")).hexdigest()[:24]


def session_resource(activity: Mapping[str, Any], observation: Mapping[str, Any], *,
                     collected_at: str) -> tuple[str, dict[str, Any]]:
    """Register the observed session before a payload can be released."""
    activity = dict(activity)
    observed = verify_specialist(activity, observation)
    resource_id = specialist_resource_id(activity["activity_id"])
    identity = {key: observed[key] for key in (
        "provider", "adapter", "host", "runtime_instance", "handle", "incarnation",
        "owner_dispatch", "task_id", "dispatch_incarnation", "worktree_id",
    )}
    resource = {
        "kind": "session", "agent_id": observed["provider"], "activity_id": activity["activity_id"],
        "scheduler_run_id": None, "worker_id": None, "wave_id": None,
        "origin_context_id": activity["context_id"], "identity": identity,
        "creation_observation": {"kind": "session", "identity": copy.deepcopy(identity),
                                   "source_ref": observed["source_ref"],
                                   "source_sha256": observed["source_sha256"], "collected_at": collected_at},
        "result_acceptance_ref": None,
        "evidence_manifest": {"files": [], "receipts": [{"ref": observed["source_ref"],
                                                              "sha256": observed["source_sha256"]}],
                              "terminal_head": None, "integrated_head": None},
        "state": "REGISTERED", "last_observation": observed["source_ref"],
        "preservation_reasons": [], "operation_id": None,
    }
    return resource_id, resource


def close_session_resource(resource: Mapping[str, Any], observation: Mapping[str, Any], *,
                           acceptance_ref: str) -> dict[str, Any]:
    """Close only the registered identity, after its result is durable."""
    try:
        from .agent_runtime import validate_observation
    except ImportError:
        from grill_core.agent_runtime import validate_observation
    closed = copy.deepcopy(dict(resource))
    observed = validate_observation(dict(observation))
    identity = {key: observed[key] for key in closed["identity"]}
    if identity != closed["identity"] or observed["close"] != "closed" or observed["activity"] != "exited":
        _fail("SESSION-CLOSE-UNPROVEN")
    if closed.get("state") != "CLOSE_PENDING":
        _fail("INVALID-RESOURCE-TRANSITION")
    _text(acceptance_ref, "resource acceptance ref")
    closed.update({"result_acceptance_ref": acceptance_ref, "state": "CLOSED"})
    return closed


def dispatch_activity(activity: Mapping[str, Any], context: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a one-shot technical payload to activity, context, fence and inputs."""
    dispatched = copy.deepcopy(dict(activity))
    payload = activity_payload(dispatched, context)
    dispatched["payload_sha256"] = _manifest_sha256(payload)
    dispatched["state"] = "DISPATCHED"
    return dispatched, payload


def record_activity_result(activity: Mapping[str, Any], *, result_ref: str, result_sha256: str,
                           output_manifest: dict[str, Any] | None, diagnostic_ref: str | None = None) -> dict[str, Any]:
    """Persist output or diagnostic before any runtime-close attempt."""
    recorded = copy.deepcopy(dict(activity))
    if recorded.get("state") != "DISPATCHED":
        _fail("INVALID-ACTIVITY-TRANSITION")
    _text(result_ref, "activity result_ref")
    _digest(result_sha256, "activity result_sha256")
    if output_manifest is None:
        _fail("activity output required")
    _output_manifest(output_manifest)
    recorded.update({"result_ref": result_ref, "result_sha256": result_sha256,
                     "output_manifest": copy.deepcopy(output_manifest), "diagnostic_ref": diagnostic_ref,
                     "state": "RESULT_RECORDED"})
    return recorded


def accept_activity(activity: Mapping[str, Any], *, context: Mapping[str, Any],
                    observation: Mapping[str, Any] | None, acceptance_ref: str,
                    review_verdict: str = "APPROVED", current_input_sha256: str | None = None) -> dict[str, Any]:
    """Revalidate identity/configuration at return, then record accepted close."""
    accepted = copy.deepcopy(dict(activity))
    if accepted.get("state") != "RESULT_RECORDED":
        _fail("INVALID-ACTIVITY-TRANSITION")
    if accepted.get("context_id") != context.get("context_id"):
        _fail("CONTEXT-FENCED")
    if accepted.get("activity_type") == "deterministic_check":
        if observation is not None:
            _fail("deterministic activity has observation")
        released_at = None
    else:
        if observation is None:
            _fail("SESSION-CLOSE-UNPROVEN")
        observed = verify_specialist(accepted, observation, require_open=False)
        if observed["close"] != "closed" or observed["activity"] != "exited":
            _fail("SESSION-CLOSE-UNPROVEN")
        released_at = observed["source_ref"]
    _text(acceptance_ref, "activity acceptance_ref")
    if review_verdict not in {"APPROVED", "CHANGES_REQUIRED"}:
        _fail("invalid activity review verdict")
    if accepted.get("activity_type") != "reviewer" and review_verdict != "APPROVED":
        _fail("invalid activity review verdict")
    if current_input_sha256 is not None:
        _digest(current_input_sha256, "current activity input sha256")
        if accepted.get("activity_type") == "reviewer" and current_input_sha256 != accepted["input_sha256"]:
            review_verdict = "STALE"
        elif current_input_sha256 != accepted["input_sha256"]:
            _fail("ACTIVITY-INPUT-DIVERGENT")
    accepted.update({"released_at": released_at, "accepted_by_context": context["context_id"],
                     "acceptance_ref": acceptance_ref, "review_verdict": review_verdict,
                     "state": "ACCEPTED"})
    return accepted


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


def cleanup_reasons(resource: Mapping[str, Any], observation: Mapping[str, Any]) -> tuple[str, ...]:
    """Derive retention from current facts; never treat an old flag as proof.

    The caller owns observation I/O.  Keeping this policy pure makes the
    session, worktree, and branch decisions independently auditable.
    """
    reasons: set[str] = set()
    kind = resource.get("kind")
    if resource.get("result_acceptance_ref") is None:
        reasons.add("RESULT_NOT_DURABLE")
    session = observation.get("session")
    if session != "closed":
        reasons.add("SESSION_ACTIVE" if session == "active" else "SESSION_CLOSE_UNCONFIRMED")
    if observation.get("identity") is not True:
        reasons.add("IDENTITY_UNPROVEN")
    elif observation.get("identity_changed") is True:
        reasons.add("IDENTITY_CHANGED")
    if kind in {"worktree", "branch"}:
        if observation.get("integrated") is not True:
            reasons.add("WORK_NOT_INTEGRATED")
        if observation.get("clean") is not True:
            reasons.add("WORKTREE_DIRTY")
        if observation.get("ignored") is True:
            reasons.add("IGNORED_CONTENT")
        if observation.get("exclusive_evidence") is True:
            reasons.add("EXCLUSIVE_EVIDENCE")
    if kind == "branch":
        if observation.get("branch_in_use") is True:
            reasons.add("BRANCH_IN_USE")
        if observation.get("ref_matches") is not True:
            reasons.add("REF_CHANGED")
    return tuple(sorted(reasons))


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
        for context in item["contexts"].values():
            if context["predecessor_context_id"] is None:
                continue
            operation = item["operations"].get(context["continuity_ref"])
            if not isinstance(operation, dict) or operation.get("kind") != "continuity-switch":
                _fail("successor context has no continuity operation")
            bridge = operation.get("intended_after", {}).get("campaign_bridge")
            if context["campaign"] is None:
                if bridge is not None:
                    _fail("pre-campaign continuity has a fictitious bridge")
                continue
            if not isinstance(bridge, dict):
                _fail("successor context has no campaign bridge")
            required_bridge = {"from_campaign", "to_campaign", "accepted_outputs", "worktree_identity"}
            if set(bridge) != required_bridge:
                _fail("invalid campaign bridge")
            old, new = campaign(bridge["from_campaign"]), campaign(bridge["to_campaign"])
            predecessor = item["contexts"][context["predecessor_context_id"]]
            if predecessor["campaign"] != old or context["campaign"] != new:
                _fail("campaign bridge diverges from contexts")
            checkpoint_id = operation.get("expected_before", {}).get("checkpoint_id")
            checkpoint = item["checkpoints"].get(checkpoint_id)
            if not isinstance(checkpoint_id, str) or not isinstance(checkpoint, dict):
                _fail("campaign bridge has no checkpoint")
            if bridge["accepted_outputs"] != checkpoint["accepted_outputs"]:
                _fail("campaign bridge accepted outputs diverge")
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
            if activity["activity_type"] == "reviewer":
                authors = _reviewer_authors(activity, item["activities"], require_accepted=resource_id is not None)
                if resource_id is not None:
                    reviewer_resource = item["resources"][resource_id]
                    reviewer_identity = reviewer_resource["identity"]
                    for author in authors:
                        author_resource_id = author["session_resource_id"]
                        if author_resource_id is None:
                            _fail("reviewer session is not independent")
                        author_resource = item["resources"].get(author_resource_id)
                        if (not isinstance(author_resource, dict)
                                or author_resource.get("kind") != "session"
                                or author_resource.get("identity") == reviewer_identity):
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
            allowed = {"PREPARED": {"PREPARED", "ACTIVE"}, "ACTIVE": {"ACTIVE", "QUIESCING", "SUPERSEDED"}, "QUIESCING": {"QUIESCING", "RELEASED", "SUPERSEDED"}, "RELEASED": {"RELEASED", "SUPERSEDED"}, "SUPERSEDED": {"SUPERSEDED"}}
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
            for key in ("kind", "context_id", "fence", "subject_ids", "input_sha256", "expected_before", "intended_after", "idempotency_key", "request", "content_ref"):
                if later.get(key) != operation.get(key): _fail("operation identity changed")
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


def task_phase_pending(tasks: Any, accepted_tasks: Any, *, target_phase: int,
                       tasks_semantic_sha256: str, dag_content_sha256: str) -> list[str]:
    """Return unfinished predecessors; acceptance is a bound receipt, not a checkbox."""
    _digest(tasks_semantic_sha256, "tasks semantic digest")
    _digest(dag_content_sha256, "DAG digest")
    if type(target_phase) is not int or target_phase < 1 or not isinstance(tasks, (list, tuple)) or not isinstance(accepted_tasks, dict):
        _fail("TASK-PHASE-PENDING")
    pending: list[str] = []
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str) or type(task.get("phase")) is not int:
            _fail("TASK-PHASE-PENDING")
        if task["phase"] >= target_phase:
            continue
        receipt = accepted_tasks.get(task["task_id"])
        if not isinstance(receipt, dict) or receipt.get("state") != "ACCEPTED":
            pending.append(task["task_id"])
            continue
        binding = receipt.get("task_binding")
        if not isinstance(binding, dict) or binding != {
            "task_id": task["task_id"], "phase": str(task["phase"]),
            "tasks_semantic_sha256": tasks_semantic_sha256, "dag_content_sha256": dag_content_sha256,
        }:
            pending.append(task["task_id"])
    return sorted(pending)


def require_task_phase_barrier(tasks: Any, accepted_tasks: Any, *, target_phase: int,
                               tasks_semantic_sha256: str, dag_content_sha256: str) -> None:
    pending = task_phase_pending(tasks, accepted_tasks, target_phase=target_phase,
                                 tasks_semantic_sha256=tasks_semantic_sha256,
                                 dag_content_sha256=dag_content_sha256)
    if pending:
        _fail("TASK-PHASE-PENDING:" + ",".join(pending))


def task_files_migration_preview(current_text: str, proposal_text: str, *, expected_sha256: str,
                                 accepted_task_ids: Any = ()) -> dict[str, Any]:
    """Hash-fence a reviewed proposal; parsing and writing stay at the CLI boundary."""
    if not isinstance(current_text, str) or not isinstance(proposal_text, str):
        _fail("TASK-FILES-INVALID")
    current_sha256 = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
    proposal_sha256 = hashlib.sha256(proposal_text.encode("utf-8")).hexdigest()
    _digest(expected_sha256, "migration expected digest")
    if current_sha256 != expected_sha256:
        _fail("TASKS-SOURCE-STALE")
    if not isinstance(accepted_task_ids, (list, tuple)) or any(not isinstance(task_id, str) for task_id in accepted_task_ids):
        _fail("TASK-FILES-INVALID")
    old_ids = set(re.findall(r"^- \[[ xX]\]\s+(T\d+)", current_text, re.MULTILINE))
    new_ids = set(re.findall(r"^- \[[ xX]\]\s+(T\d+)", proposal_text, re.MULTILINE))
    if not set(accepted_task_ids).issubset(new_ids) or not set(accepted_task_ids).issubset(old_ids):
        _fail("TASK-RESULT-DIVERGENT")
    return {"verdict": "PREVIEW", "current_sha256": current_sha256, "proposal_sha256": proposal_sha256,
            "preserved_task_ids": sorted(old_ids & new_ids), "added_task_ids": sorted(new_ids - old_ids),
            "accepted_task_ids": sorted(accepted_task_ids)}


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


def checkpoint_request(*, store_origin: dict[str, Any], work_id: str, operation_id: str,
                       context_id: str, step: str, state: str,
                       evidence: list[dict[str, str]], reason: str,
                       attestation: dict[str, str] | None,
                       supersedes_attestation: dict[str, str] | None,
                       initialize_legacy: bool, from_step: str | None) -> dict[str, Any]:
    """Return the immutable request identity used for checkpoint retries."""
    request = {
        "schema": CHECKPOINT_REQUEST_SCHEMA, "store_origin": copy.deepcopy(store_origin),
        "work_id": work_id, "operation_id": operation_id, "context_id": context_id,
        "step": step, "state": state, "evidence": copy.deepcopy(evidence),
        "reason": reason, "attestation": copy.deepcopy(attestation),
        "supersedes_attestation": copy.deepcopy(supersedes_attestation),
        "initialize_legacy": initialize_legacy, "from_step": from_step,
    }
    validate_checkpoint_request(request)
    return request


def validate_checkpoint_request(value: Any) -> dict[str, Any]:
    required = {"schema", "store_origin", "work_id", "operation_id", "context_id", "step", "state", "evidence", "reason", "attestation", "supersedes_attestation", "initialize_legacy", "from_step"}
    value = _object(value, required, set(), "checkpoint request")
    if value["schema"] != CHECKPOINT_REQUEST_SCHEMA:
        _fail("invalid checkpoint request schema")
    for key in ("work_id", "operation_id", "context_id", "step"):
        _id(value[key], f"checkpoint request {key}")
    if value["state"] not in {"in-progress", "complete", "blocked"}:
        _fail("invalid checkpoint request state")
    if not isinstance(value["store_origin"], dict):
        _fail("invalid checkpoint request store_origin")
    _json(value["store_origin"], "checkpoint request store_origin")
    if not isinstance(value["evidence"], list):
        _fail("invalid checkpoint request evidence")
    paths = []
    for entry in value["evidence"]:
        entry = _object(entry, {"path", "sha256"}, set(), "checkpoint request evidence")
        _safe_path(entry["path"]); _digest(entry["sha256"], "checkpoint request evidence sha256")
        paths.append(entry["path"])
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        _fail("checkpoint request evidence is not canonical")
    if not isinstance(value["reason"], str) or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value["reason"]):
        _fail("invalid checkpoint request reason")
    _ref(value["attestation"], "checkpoint request attestation", nullable=True)
    _ref(value["supersedes_attestation"], "checkpoint request supersedes_attestation", nullable=True)
    if type(value["initialize_legacy"]) is not bool:
        _fail("invalid checkpoint request initialize_legacy")
    _text(value["from_step"], "checkpoint request from_step", nullable=True)
    return value


def _state_bytes(value: Any, label: str, *, nullable: bool = False) -> bytes | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        _fail(f"invalid {label}")
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise OrchestrationError(f"invalid {label}") from exc
    if len(raw) > MAX_CHECKPOINT_STATE_BYTES:
        _fail(f"{label} exceeds limit")
    return raw


def validate_checkpoint_content(value: Any) -> dict[str, Any]:
    """Validate the immutable payload written before its checkpoint receipt."""
    required = {"schema", "work_id", "operation_id", "request", "checkpoint", "before_base64", "state_write", "binding_transition", "result"}
    value = _object(value, required, set(), "checkpoint content")
    if value["schema"] != CHECKPOINT_CONTENT_SCHEMA:
        _fail("invalid checkpoint content schema")
    for key in ("work_id", "operation_id"):
        _id(value[key], f"checkpoint content {key}")
    request = validate_checkpoint_request(value["request"])
    if request["work_id"] != value["work_id"] or request["operation_id"] != value["operation_id"]:
        _fail("checkpoint content request mismatch")
    _checkpoint(value["checkpoint"].get("checkpoint_id") if isinstance(value["checkpoint"], dict) else "", value["checkpoint"])
    state_write = _object(value["state_write"], {"work_id", "destination", "before_sha256", "after_base64", "after_sha256", "expected_store_revision", "expected_journal_anchor"}, set(), "checkpoint state_write")
    if state_write["work_id"] != value["work_id"]:
        _fail("checkpoint state_write work id mismatch")
    _safe_path(state_write["destination"])
    _nullable_digest(state_write["before_sha256"], "checkpoint state_write before_sha256")
    after = _state_bytes(state_write["after_base64"], "checkpoint state_write after_base64")
    if hashlib.sha256(after).hexdigest() != state_write["after_sha256"]:
        _fail("checkpoint state_write after digest mismatch")
    _digest(state_write["after_sha256"], "checkpoint state_write after_sha256")
    if type(state_write["expected_store_revision"]) is not int or state_write["expected_store_revision"] < 1:
        _fail("invalid checkpoint state_write revision")
    if not isinstance(state_write["expected_journal_anchor"], dict):
        _fail("invalid checkpoint state_write journal anchor")
    _json(state_write["expected_journal_anchor"], "checkpoint state_write journal anchor")
    before = _state_bytes(value["before_base64"], "checkpoint before_base64", nullable=True)
    if (before is None) != (state_write["before_sha256"] is None):
        _fail("checkpoint before absence mismatch")
    if before is not None and hashlib.sha256(before).hexdigest() != state_write["before_sha256"]:
        _fail("checkpoint before digest mismatch")
    if value["binding_transition"] is not None:
        if not isinstance(value["binding_transition"], dict):
            _fail("invalid checkpoint binding_transition")
        _json(value["binding_transition"], "checkpoint binding_transition")
    result = _object(value["result"], {"work_id", "context_id", "epoch", "operation_id", "checkpoint_id", "step", "state", "evidence", "reason", "execution_branch", "supersedes", "current_step"}, set(), "checkpoint result")
    if result["work_id"] != value["work_id"] or result["operation_id"] != value["operation_id"] or result["checkpoint_id"] != value["checkpoint"]["checkpoint_id"]:
        _fail("checkpoint result correlation mismatch")
    _id(result["context_id"], "checkpoint result context")
    if type(result["epoch"]) is not int or result["epoch"] < 1:
        _fail("invalid checkpoint result epoch")
    for key in ("step", "state", "execution_branch", "current_step"):
        _text(result[key], f"checkpoint result {key}", nullable=key in {"execution_branch", "current_step"})
    if not isinstance(result["reason"], str) or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in result["reason"]):
        _fail("invalid checkpoint result reason")
    if not isinstance(result["evidence"], list):
        _fail("invalid checkpoint result evidence")
    _ref(result["supersedes"], "checkpoint result supersedes", nullable=True)
    return value


def checkpoint_content_sha256(value: dict[str, Any]) -> str:
    validate_checkpoint_content(value)
    return _manifest_sha256(value)
