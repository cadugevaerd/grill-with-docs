"""Observed runtime boundary; caller supplied JSON is never evidence."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

_HEX = re.compile(r"^[0-9a-f]{64}$")
_OBSERVATION_KEYS = {
    "schema", "adapter", "provider", "handle", "incarnation",
    "dispatch_incarnation", "runtime_instance", "host", "owner_dispatch",
    "task_id", "worktree_id", "source_ref", "source_sha256",
    "requested_model", "requested_effort", "effective_model",
    "effective_effort", "resolved_model_id", "activity", "close",
}
_ORCA_CAPABILITIES = {
    "orchestration.worker-launch-preferences.v1",
    "orchestration.federation-structured-read.v1",
    "orchestration.federation-lifecycle-settlement.v1",
    "orchestration.federation-release-archive.v1",
}


class RuntimeError(ValueError):
    pass


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _source_digest(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid {label} response") from exc
    if not isinstance(value, dict) or not value.get("ok") or not isinstance(value.get("result"), dict):
        _fail(f"invalid {label} response")
    return value["result"]


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"missing {label}")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"missing {label}")
    return value


def _same(label: str, *values: Any) -> str:
    values = tuple(_string(value, label) for value in values)
    if len(set(values)) != 1:
        _fail(f"uncorrelated {label}")
    return values[0]


def _identity(value: dict[str, Any]) -> tuple[Any, ...]:
    keys = (
        "adapter", "provider", "handle", "incarnation", "dispatch_incarnation",
        "runtime_instance", "host", "owner_dispatch", "task_id", "worktree_id",
    )
    if any(not value.get(key) for key in keys):
        _fail("runtime identity incomplete")
    return tuple(value[key] for key in keys)


def validate_observation(value: Any, source: tuple[bytes, ...] | None = None) -> dict[str, Any]:
    """Validate the closed normalized shape after an adapter observed it."""
    if not isinstance(value, dict):
        _fail("observation must be object")
    if set(value) != _OBSERVATION_KEYS or value.get("schema") != "grill-agent-observation/v1":
        _fail("invalid observation keys")
    _identity(value)
    if value["adapter"] != "orca" or value["provider"] not in {"codex", "claude"}:
        _fail("unknown runtime adapter or provider")
    if not isinstance(value["source_ref"], str) or not value["source_ref"]:
        _fail("invalid observation source")
    if not isinstance(value["source_sha256"], str) or not _HEX.fullmatch(value["source_sha256"]):
        _fail("invalid observation source")
    if source is not None and (not all(isinstance(raw, bytes) for raw in source) or value["source_sha256"] != _source_digest(*source)):
        _fail("observation digest mismatch")
    for key in (
        "requested_model", "requested_effort", "effective_model", "effective_effort",
        "resolved_model_id",
    ):
        if value[key] is not None and (not isinstance(value[key], str) or not value[key]):
            _fail(f"invalid {key}")
    if value["activity"] not in {"active", "idle", "exited", "unknown"}:
        _fail("invalid observation state")
    if value["close"] not in {"not_requested", "pending", "closed", "unknown", "preserved"}:
        _fail("invalid observation state")
    return value


def _launch_pair(launch: dict[str, Any], worker: dict[str, Any]) -> tuple[str, str, str, str, str]:
    launch_options = _mapping(launch.get("launch"), "launch")
    worker_options = _mapping(_mapping(worker.get("startOptions"), "worker startOptions").get("launch"), "worker launch")
    requested = _mapping(launch_options.get("requested"), "requested launch")
    effective = _mapping(launch_options.get("effective"), "effective launch")
    worker_requested = _mapping(worker_options.get("requested"), "worker requested launch")
    worker_effective = _mapping(worker_options.get("effective"), "worker effective launch")
    provider = _same("provider", effective.get("agent"), worker_effective.get("agent"))
    requested_model = _same("requested model", requested.get("model"), worker_requested.get("model"))
    requested_effort = _same("requested effort", requested.get("effort"), worker_requested.get("effort"))
    effective_model = _same("effective model", effective.get("model"), worker_effective.get("model"))
    effective_effort = _same("effective effort", effective.get("effort"), worker_effective.get("effort"))
    return requested_model, requested_effort, effective_model, effective_effort, provider


def _orca_observation(source_ref: str, launch_raw: bytes, show_raw: bytes) -> dict[str, Any]:
    """Normalize only fields that occur in correlated public Orca responses."""
    launch = _object(launch_raw, "Orca launch")
    show = _object(show_raw, "Orca worker-show")
    dispatch = _mapping(show.get("dispatch"), "dispatch")
    worker = _mapping(show.get("worker"), "worker")
    resource = _mapping(show.get("terminalResource"), "terminal resource")
    host_scope = _mapping(dispatch.get("hostScope"), "dispatch host")
    terminal = show.get("terminal")
    if terminal is not None and not isinstance(terminal, dict):
        _fail("invalid terminal")
    requested_model, requested_effort, effective_model, effective_effort, provider = _launch_pair(launch, worker)
    dispatch_id = _same("dispatch", launch.get("dispatchId"), dispatch.get("id"), worker.get("dispatchId"), resource.get("ownerDispatchId"))
    if dispatch_id not in source_ref:
        _fail("uncorrelated observation source")
    projection = _mapping(show.get("projection"), "projection")
    task_id = _same("task", launch.get("taskId"), dispatch.get("taskId"), projection.get("taskId"))
    worktree_id = _same("worktree", worker.get("worktreeId"), resource.get("worktreeId"))
    runtime_instance = _same("runtime instance", worker.get("runtimeEpoch"), resource.get("endpointId"))
    dispatch_incarnation = _string(resource.get("endpointIncarnation"), "dispatch incarnation")
    incarnation = _string(_mapping(launch.get("prompt"), "launch prompt").get("processIncarnation"), "launch process incarnation")
    handle = _same("terminal handle", worker.get("agentTerminalHandle"), resource.get("terminalHandle"))
    host = _string(host_scope.get("hostId"), "host")
    liveness = projection.get("liveness")
    if terminal is not None:
        _same("terminal handle", handle, terminal.get("handle"))
        _same("worktree", worktree_id, terminal.get("worktreeId"))
        _same("host", host, terminal.get("executionHostId"))
        _same("incarnation", incarnation, terminal.get("incarnationId"))
    projection_provider = projection.get("provider")
    if projection_provider is not None:
        _same("provider", provider, _mapping(projection_provider, "projection provider").get("id"))
    projection_host = projection.get("host")
    if projection_host is not None:
        _same("host", host, _mapping(projection_host, "projection host").get("id"))
    closed = (resource.get("releaseState") == "released" and isinstance(liveness, dict)
              and worker.get("agentWait", object()) is not None and dispatch.get("status") == "completed"
              and worker.get("stage") == "settled" and worker.get("state") in {"succeeded", "failed"}
              and liveness.get("verdict") == "exited" and liveness.get("source") == "resource_release"
              and _mapping(projection.get("resource"), "release resource").get("releaseState") == "released"
              and _mapping(projection.get("resource"), "release resource").get("ownerDispatchId") == dispatch_id)
    if terminal is None and not closed:
        _fail("current session incarnation unproven")
    close, activity = "not_requested", "unknown"
    if resource.get("releaseState") == "not_requested":
        if isinstance(liveness, dict) and liveness.get("verdict") == "exited":
            activity = "exited"
        elif isinstance(liveness, dict) and liveness.get("verdict") == "live" and liveness.get("source") == "agent_status":
            activity = {"ready": "active", "running": "active", "idle": "idle"}.get(worker.get("state"), "unknown")
    elif resource.get("releaseState") in {"release_pending", "pending"}:
        close = "pending"
    elif resource.get("releaseState") == "released":
        if closed:
            close, activity = "closed", "exited"
        else:
            close = "unknown"
    resolved_model_id = effective_model if requested_model == effective_model else None
    return validate_observation({
        "schema": "grill-agent-observation/v1", "adapter": "orca", "provider": provider,
        "handle": handle, "incarnation": incarnation, "dispatch_incarnation": dispatch_incarnation,
        "runtime_instance": runtime_instance, "host": host, "owner_dispatch": dispatch_id,
        "task_id": task_id, "worktree_id": worktree_id, "source_ref": source_ref,
        "source_sha256": _source_digest(launch_raw, show_raw), "requested_model": requested_model,
        "requested_effort": requested_effort, "effective_model": effective_model,
        "effective_effort": effective_effort, "resolved_model_id": resolved_model_id,
        "activity": activity, "close": close,
    }, (launch_raw, show_raw))


@dataclass
class RuntimeBoundary:
    """Known adapter seam. Its callables return native public response bytes."""

    adapter: str
    source_ref: str
    capabilities: set[str]
    probe: Callable[[], tuple[bytes, bytes]]
    observe: Callable[[], tuple[bytes, bytes]]
    request_close: Callable[[], bytes]
    read_after_close: Callable[[], tuple[bytes, bytes]]
    _closed: bool = field(default=False, init=False)
    # Process-local only; T005 owns durable operation recovery across boundaries.
    _close_pending: bool = field(default=False, init=False)

    def _supported(self) -> None:
        if self.adapter != "orca" or not isinstance(self.source_ref, str) or not self.source_ref or not _ORCA_CAPABILITIES.issubset(self.capabilities):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")

    def _read(self, fn: Callable[[], tuple[bytes, bytes]]) -> dict[str, Any]:
        self._supported()
        pair = fn()
        if not isinstance(pair, tuple) or len(pair) != 2 or not all(isinstance(raw, bytes) for raw in pair):
            _fail("adapter did not return launch and worker-show bytes")
        return _orca_observation(self.source_ref, *pair)

    def verified(self, requested_model: str, requested_effort: str) -> dict[str, Any]:
        probed = self._read(self.probe)
        observation = self._read(self.observe)
        if _identity(probed) != _identity(observation):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        if not isinstance(requested_model, str) or not requested_model or not isinstance(requested_effort, str) or not requested_effort or observation["effective_model"] != requested_model or observation["effective_effort"] != requested_effort or observation["resolved_model_id"] != observation["effective_model"] or observation["activity"] not in {"active", "idle"} or observation["close"] != "not_requested":
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        return observation

    def revalidate(self, expected: dict[str, Any]) -> dict[str, Any]:
        """Read current runtime facts before accepting a specialist return."""
        expected = validate_observation(expected)
        observed = self._read(self.observe)
        if (_identity(observed) != _identity(expected)
                or observed["effective_model"] != expected["effective_model"]
                or observed["effective_effort"] != expected["effective_effort"]
                or observed["resolved_model_id"] != expected["resolved_model_id"]
                or observed["activity"] not in {"active", "idle"}
                or observed["close"] != "not_requested"):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        return observed

    def close(self, expected: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            _fail("runtime close already confirmed")
        expected = validate_observation(expected)
        self._supported()
        if not self._close_pending:
            self._close_pending = True
            release = _object(self.request_close(), "Orca worker-release")
            if release.get("dispatchId") != expected["owner_dispatch"] or release.get("state") != "released" or release.get("processAction") != "closed_agent_terminal" or _mapping(release.get("archive"), "release archive").get("status") != "captured":
                _fail("runtime close unconfirmed")
        observed = self._read(self.read_after_close)
        if _identity(observed) != _identity(expected) or observed["close"] != "closed" or observed["activity"] != "exited":
            _fail("runtime close unconfirmed")
        self._closed = True
        self._close_pending = False
        return observed
